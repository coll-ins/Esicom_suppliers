import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { BackLink, Band, Button, Card, Check, Choice, ErrorBox, Field, Input, Loading, Notice, PageHeader, useLoad } from '../components/ui'
import { get, post } from '../lib/api'
import { kes, saleTotals } from '../lib/money'
import { textError, wholeKes, wholeQty } from '../lib/validate'

// Credit part or all of an invoice: pick lines and quantities, optionally put stock back.
export default function CreditNote() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [doc, error, reload] = useLoad(() => get(`/documents/${id}/`), [id])
  const [rows, setRows] = useState(null)
  const [extra, setExtra] = useState({ description: '', amount: '' })
  const [reason, setReason] = useState('')
  const [overpay, setOverpay] = useState('refund')
  const [busy, setBusy] = useState(false)
  const [saveError, setSaveError] = useState(null)
  const [errors, setErrors] = useState({})

  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (!doc) return <Loading />
  const lines = rows || doc.lines.map((l) => ({ ...l, credit: '0', restock: false }))

  const items = []
  for (const l of lines) {
    const q = wholeQty(l.credit, 'Quantity', { min: 0 }).value
    if (q) items.push({ description: l.description, qty: q, unit_price: l.unit_price, vat_exempt: l.vat_exempt, product_id: l.product_id || undefined, restock: l.restock })
  }
  const extraAmt = wholeKes(extra.amount, 'Amount', { min: 1 }).value
  if (extraAmt) items.push({ description: extra.description || 'Discount', qty: 1, unit_price: extraAmt, vat_exempt: false })
  const totals = saleTotals(items.map((i) => ({ qty: i.qty, unitPrice: i.unit_price, vatExempt: i.vat_exempt })), doc.vat_percent)
  const alreadyPaid = doc.total - doc.balance
  const refundable = Math.max(totals.total - doc.balance, 0)

  const save = async () => {
    const e = {}
    const r = textError(reason, 'Reason', { min: 3, max: 200 })
    if (r) e.reason = r
    if (!items.length) e.items = 'Enter a quantity to credit on at least one line, or an amount.'
    lines.forEach((l, i) => {
      const q = wholeQty(l.credit, 'Quantity', { min: 0 })
      if (q.error) e[`q${i}`] = q.error
      else if (q.value > l.qty) e[`q${i}`] = `At most ${l.qty}.`
    })
    if (extra.amount && wholeKes(extra.amount, 'Amount', { min: 1 }).error) e.extra = wholeKes(extra.amount, 'Amount', { min: 1 }).error
    setErrors(e)
    if (Object.keys(e).length) return
    setBusy(true)
    setSaveError(null)
    try {
      const cn = await post(`/documents/${doc.id}/credit-note/`, { items, reason, overpay })
      navigate(`/documents/${cn.id}`, { replace: true })
    } catch (err) {
      setSaveError(err)
    } finally {
      setBusy(false)
    }
  }

  const setRow = (i, patch) => setRows(lines.map((l, j) => (j === i ? { ...l, ...patch } : l)))

  return (
    <>
      <PageHeader back={<BackLink to={`/documents/${doc.id}`} label={doc.number} />} title={`Credit note for ${doc.number}`}>
        Use this to correct an issued invoice: returned goods, wrong price, or a discount. The invoice itself never changes.
      </PageHeader>
      <ErrorBox error={saveError} />
      <div className="mt-4 grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start">
        <Card className="grid gap-4">
          <h2 className="text-[18px]">What are you crediting?</h2>
          {errors.items ? <p className="m-0 text-danger">{errors.items}</p> : null}
          {lines.map((l, i) => (
            <div key={i} className="grid gap-3 rounded-[var(--radius-control)] border border-line p-3 sm:grid-cols-[minmax(0,1fr)_120px] sm:items-start">
              <div>
                <div className="font-bold">{l.description}</div>
                <div className="text-sm text-muted">{l.qty} sold at {kes(l.unit_price)}</div>
                {l.product_id ? <Check label="Put back in stock" hint="Tick if the items came back and can be sold again." checked={l.restock} onChange={(v) => setRow(i, { restock: v })} /> : null}
              </div>
              <Field label="Qty to credit" error={errors[`q${i}`]}>
                {(p) => <Input {...p} inputMode="numeric" value={l.credit} onChange={(e) => setRow(i, { credit: e.target.value })} />}
              </Field>
            </div>
          ))}
          <details className="rounded-[var(--radius-control)] border border-line bg-paper p-3">
            <summary className="min-h-11 cursor-pointer content-center font-bold">Credit an amount instead (discount)</summary>
            <div className="mt-3 grid gap-4 sm:grid-cols-2">
              <Field label="Description" hint="Example: Discount agreed on 12 Nov.">
                {(p) => <Input {...p} value={extra.description} maxLength={200} onChange={(e) => setExtra({ ...extra, description: e.target.value })} />}
              </Field>
              <Field label="Amount before VAT (KES)" hint="Whole shillings. VAT is taken off too." error={errors.extra}>
                {(p) => <Input {...p} inputMode="numeric" value={extra.amount} onChange={(e) => setExtra({ ...extra, amount: e.target.value })} />}
              </Field>
            </div>
          </details>
          <Field label="Reason" hint="Printed on the credit note. Example: 2 reams returned damaged." error={errors.reason}>
            {(p) => <Input {...p} value={reason} maxLength={200} onChange={(e) => setReason(e.target.value)} />}
          </Field>
        </Card>
        <aside className="grid gap-3 lg:sticky lg:top-6">
          <Card className="grid gap-3">
            <Band label="Credit total" amount={totals.total} />
            <p className="m-0 text-sm text-muted">Invoice balance now {kes(doc.balance)}. Already paid {kes(alreadyPaid)}.</p>
            {refundable > 0 ? (
              <div className="grid gap-2">
                <Notice tone="info">{kes(refundable)} of this was already paid.</Notice>
                <Choice label="Money already paid" value={overpay} onChange={setOverpay} options={[{ value: 'refund', label: 'Refund it' }, { value: 'credit', label: 'Keep as credit' }]} />
              </div>
            ) : null}
            <Button loading={busy} onClick={save}>Issue credit note</Button>
          </Card>
        </aside>
      </div>
    </>
  )
}
