import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CustomerPicker, ProductSearch, emptyNewCustomer, newCustomerErrors } from '../components/pickers'
import Share from '../components/Share'
import {
  Band, Button, ButtonLink, Card, Check, Choice, ErrorBox, Field, Input, Notice, PageHeader, TotalsRows, todayIso, useLoad,
} from '../components/ui'
import { get, post } from '../lib/api'
import { useAuth } from '../lib/auth'
import { kes, saleTotals } from '../lib/money'
import { stockError, textError, wholeKes, wholeQty } from '../lib/validate'

let nextKey = 1
const blankCustom = { description: '', qty: '1', unitPrice: '', vatExempt: false }

export default function Sell({ mode }) {
  const quotation = mode === 'quotation'
  const { me } = useAuth()
  const percent = me.vat_percent
  const [params] = useSearchParams()
  const leadId = params.get('lead')
  const [products] = useLoad(() => get('/products/'))
  const [customer, setCustomer] = useState(null)
  const [lines, setLines] = useState([])
  const [custom, setCustom] = useState(blankCustom)
  const [customErr, setCustomErr] = useState({})
  const [payMode, setPayMode] = useState('now')
  const [pay, setPay] = useState({ method: 'mpesa', amount: '', reference: '', overpay: 'refund', receipt: false })
  const [dueOn, setDueOn] = useState('')
  const [validUntil, setValidUntil] = useState('')
  const [step, setStep] = useState('edit')
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [lead, setLead] = useState(null)

  useEffect(() => {
    if (!quotation || !leadId) return
    get('/leads/').then((rows) => {
      const l = rows.find((r) => String(r.id) === leadId)
      if (!l) return
      setLead(l)
      setCustomer({ kind: 'new', fields: { ...emptyNewCustomer, name: l.company || l.name, phone: l.phone, email: l.email } })
    }).catch(() => {})
  }, [quotation, leadId])

  // Quantities and prices are typed as text; parse once for totals and checks.
  const parsed = lines.map((l) => ({ ...l, q: wholeQty(l.qty), p: wholeKes(l.unitPrice, 'Unit price') }))
  const valid = parsed.filter((l) => l.q.value && l.p.value !== undefined)
  const totals = saleTotals(valid.map((l) => ({ qty: l.q.value, unitPrice: l.p.value, vatExempt: l.vatExempt })), percent)

  const stockProblems = useMemo(() => {
    if (quotation) return {}
    const wanted = {}
    for (const l of parsed) if (l.productId && l.q.value) wanted[l.productId] = (wanted[l.productId] || 0) + l.q.value
    const out = {}
    for (const l of parsed) {
      if (!l.productId) continue
      const msg = stockError(l.description, wanted[l.productId] || 0, l.onHand)
      if (msg) out[l.key] = msg
    }
    return out
  }, [parsed, quotation])

  const isWalkIn = customer?.kind === 'walkin'
  const effectivePay = isWalkIn ? 'now' : payMode
  const amount = wholeKes(pay.amount === '' ? String(totals.total) : pay.amount, 'Amount paid', { min: 1 })
  const overpaid = amount.value !== undefined ? amount.value - totals.total : 0
  const onTab = !quotation && effectivePay === 'credit' &&
    (customer?.kind === 'existing' ? customer.customer.billing === 'tab' : customer?.fields?.billing === 'tab')

  const addProduct = (p) => {
    const existing = lines.find((l) => l.productId === p.id)
    if (existing) {
      setLines(lines.map((l) => (l === existing ? { ...l, qty: String((wholeQty(l.qty).value || 0) + 1) } : l)))
      return
    }
    setLines([...lines, { key: nextKey++, productId: p.id, description: p.name, qty: '1', unitPrice: String(p.price), vatExempt: p.vat_exempt, onHand: p.on_hand, unit: p.unit }])
  }

  const addCustom = () => {
    const e = {
      description: textError(custom.description, 'Description', { min: 2, max: 200 }),
      qty: wholeQty(custom.qty).error || '',
      unitPrice: wholeKes(custom.unitPrice, 'Unit price').error || '',
    }
    setCustomErr(e)
    if (Object.values(e).some(Boolean)) return
    setLines([...lines, { key: nextKey++, productId: null, ...custom }])
    setCustom(blankCustom)
  }

  const update = (key, patch) => setLines(lines.map((l) => (l.key === key ? { ...l, ...patch } : l)))

  const check = () => {
    const e = {}
    if (!customer) e.customer = 'Pick a customer, add a new one, or choose Walk-in.'
    if (customer?.kind === 'new') Object.assign(e, Object.fromEntries(Object.entries(newCustomerErrors(customer.fields)).filter(([, v]) => v)))
    if (!lines.length) e.lines = 'Add at least one item.'
    for (const l of parsed) {
      if (l.q.error) e[`qty${l.key}`] = l.q.error
      if (l.p.error) e[`price${l.key}`] = l.p.error
    }
    if (Object.keys(stockProblems).length) e.stock = 'Some items are over the stock on hand.'
    if (!quotation && effectivePay === 'now') {
      if (amount.error) e.amount = amount.error
      else if (amount.value < totals.total) e.amount = `Paid now must cover the total of ${kes(totals.total)}. For less, choose On credit.`
      if (pay.method === 'mpesa' && !pay.reference.trim()) e.reference = 'Enter the M-Pesa code from the message, for example TKB7XY12AB.'
    }
    setErrors(e)
    return !Object.keys(e).length
  }

  const customerBody = () => {
    if (customer.kind === 'walkin') return { walk_in: true }
    if (customer.kind === 'existing') return { customer_id: customer.customer.id }
    const f = customer.fields
    return { new_customer: { name: f.name, phone: f.phone, email: f.email, billing: f.billing } }
  }

  const save = async () => {
    setBusy(true)
    setError(null)
    try {
      const items = parsed.map((l) =>
        l.productId
          ? { product_id: l.productId, qty: l.q.value, unit_price: l.p.value, description: l.description }
          : { description: l.description, qty: l.q.value, unit_price: l.p.value, vat_exempt: l.vatExempt },
      )
      if (quotation) {
        const doc = await post('/quotations/', { ...customerBody(), items, valid_until: validUntil || undefined, lead_id: lead?.id })
        setResult({ quotation: doc })
      } else {
        const body = { ...customerBody(), items, due_on: effectivePay === 'credit' && dueOn ? dueOn : undefined }
        if (effectivePay === 'now') {
          body.paid_now = { amount: amount.value, method: pay.method, reference: pay.reference.trim(), overpay: pay.overpay }
          body.receipt = pay.receipt
        }
        setResult(await post('/sales/', body))
      }
      setStep('done')
      window.scrollTo(0, 0)
    } catch (e) {
      setError(e)
      setStep('edit')
    } finally {
      setBusy(false)
    }
  }

  const reset = () => {
    setCustomer(null); setLines([]); setPay({ method: 'mpesa', amount: '', reference: '', overpay: 'refund', receipt: false })
    setPayMode('now'); setDueOn(''); setValidUntil(''); setResult(null); setErrors({}); setStep('edit'); setError(null)
  }

  if (step === 'done' && result) {
    const doc = result.quotation || result.invoice
    return (
      <>
        <PageHeader title={quotation ? 'Quotation saved' : result.on_tab ? 'Added to the tab' : 'Sale saved'} />
        <div className="grid max-w-[720px] gap-5">
          {result.alert ? <Notice tone="warn">{result.alert}</Notice> : null}
          {result.on_tab ? (
            <Card className="grid gap-3">
              <p className="m-0">The items are on {result.customer.name}'s tab. Stock is already taken off. Print the invoice from their page whenever you want.</p>
              <ButtonLink to={`/customers/${result.customer.id}`} variant="primary">Open {result.customer.name}</ButtonLink>
            </Card>
          ) : null}
          {doc ? (
            <Card className="grid gap-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <Link to={`/documents/${doc.id}`} className="font-display text-[20px] font-bold text-navy underline">{doc.number}</Link>
                <span className="text-muted">{doc.customer.name}</span>
              </div>
              <Band label={quotation ? 'Total (KES)' : doc.balance > 0 ? 'Total due' : 'Paid in full'} amount={doc.total} />
              {result.overpaid > 0 ? <Notice tone="info">Extra paid: {kes(result.overpaid)}. {pay.overpay === 'refund' ? 'Give it back to the customer now.' : 'Kept as credit for their next invoice.'}</Notice> : null}
              <Share doc={doc} />
            </Card>
          ) : null}
          {result.receipt ? (
            <Card className="grid gap-3">
              <h2 className="text-[18px]">Receipt {result.receipt.number}</h2>
              <Share doc={result.receipt} />
            </Card>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button onClick={reset}>{quotation ? 'New quotation' : 'Record another sale'}</Button>
            <ButtonLink to="/">Back to Home</ButtonLink>
          </div>
        </div>
      </>
    )
  }

  const productList = products || []

  return (
    <>
      <PageHeader title={quotation ? 'New quotation' : 'Record a sale'}>
        {quotation ? 'Prices for the customer to approve. Stock is not touched until it becomes an invoice.' : 'Pick the customer, add items, then save. Stock comes off when you save.'}
      </PageHeader>
      <ErrorBox error={error} />
      {lead ? <Notice tone="info">From website lead: {lead.name}. They asked for: {lead.needs}</Notice> : null}

      <div className="mt-4 grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start">
        <div className="grid gap-6">
          <Card className="grid gap-4">
            <h2 className="text-[18px]">1. Customer</h2>
            <CustomerPicker value={customer} onChange={setCustomer} allowWalkIn={!quotation} errors={errors} />
          </Card>

          <Card className="grid gap-5">
            <h2 className="text-[18px]">2. Items</h2>
            <ProductSearch products={productList.filter((p) => p.active)} onPick={addProduct} />
            {errors.lines ? <p className="m-0 text-danger">{errors.lines}</p> : null}
            {lines.length ? (
              <ul className="grid gap-2">
                {parsed.map((l) => (
                  <li key={l.key} className="grid gap-3 rounded-[var(--radius-control)] border border-line p-3 sm:grid-cols-[minmax(0,1fr)_96px_128px_auto] sm:items-start">
                    <div className="min-w-0">
                      <div className="font-bold">{l.description}</div>
                      <div className="text-sm text-muted">
                        {l.productId ? `${l.onHand} in stock` : 'Custom line, no stock'}{l.vatExempt ? ', VAT exempt' : ''}
                      </div>
                      {stockProblems[l.key] ? <div className="text-sm text-danger">{stockProblems[l.key]}</div> : null}
                    </div>
                    <Field label="Qty" error={errors[`qty${l.key}`]}>
                      {(p) => <Input {...p} inputMode="numeric" value={l.qty} onChange={(e) => update(l.key, { qty: e.target.value })} />}
                    </Field>
                    <Field label="Unit price" error={errors[`price${l.key}`]}>
                      {(p) => <Input {...p} inputMode="numeric" value={l.unitPrice} onChange={(e) => update(l.key, { unitPrice: e.target.value })} />}
                    </Field>
                    <Button variant="quiet" className="sm:mt-7" onClick={() => setLines(lines.filter((x) => x.key !== l.key))} aria-label={`Remove ${l.description}`}>Remove</Button>
                  </li>
                ))}
              </ul>
            ) : null}

            <details className="rounded-[var(--radius-control)] border border-line bg-paper p-3">
              <summary className="min-h-11 cursor-pointer content-center font-bold">Add a custom line (service, branding job, special order)</summary>
              <div className="mt-3 grid gap-4">
                <Field label="Description" hint="Example: Branded polo shirts, navy, logo on chest." error={customErr.description}>
                  {(p) => <Input {...p} value={custom.description} maxLength={200} onChange={(e) => setCustom({ ...custom, description: e.target.value })} />}
                </Field>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Qty" hint="Whole number. Example: 20." error={customErr.qty}>
                    {(p) => <Input {...p} inputMode="numeric" value={custom.qty} onChange={(e) => setCustom({ ...custom, qty: e.target.value })} />}
                  </Field>
                  <Field label="Unit price (KES)" hint="Before VAT. Example: 1150." error={customErr.unitPrice}>
                    {(p) => <Input {...p} inputMode="numeric" value={custom.unitPrice} onChange={(e) => setCustom({ ...custom, unitPrice: e.target.value })} />}
                  </Field>
                </div>
                <Check label="VAT exempt" hint="Tick only if this item carries no VAT." checked={custom.vatExempt} onChange={(v) => setCustom({ ...custom, vatExempt: v })} />
                <Button variant="secondary" onClick={addCustom} className="justify-self-start">Add line</Button>
              </div>
            </details>
          </Card>

          {!quotation ? (
            <Card className="grid gap-4">
              <h2 className="text-[18px]">3. Payment</h2>
              <Choice
                label="Payment"
                value={effectivePay}
                onChange={setPayMode}
                options={[{ value: 'now', label: 'Paid now' }, { value: 'credit', label: 'On credit', disabled: isWalkIn }]}
              />
              {effectivePay === 'now' ? (
                <div className="grid gap-4">
                  <Choice label="Method" value={pay.method} onChange={(v) => setPay({ ...pay, method: v })} options={[{ value: 'mpesa', label: 'M-Pesa' }, { value: 'cash', label: 'Cash' }, { value: 'bank', label: 'Bank' }]} />
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field label="Amount received (KES)" hint={`Whole shillings. The total is ${kes(totals.total)}.`} error={errors.amount}>
                      {(p) => <Input {...p} inputMode="numeric" placeholder={String(totals.total)} value={pay.amount} onChange={(e) => setPay({ ...pay, amount: e.target.value })} />}
                    </Field>
                    <Field label={pay.method === 'mpesa' ? 'M-Pesa code' : 'Reference'} optional={pay.method !== 'mpesa'} hint={pay.method === 'mpesa' ? 'From the M-Pesa message. Example: TKB7XY12AB.' : 'Cheque or slip number, if any.'} error={errors.reference}>
                      {(p) => <Input {...p} value={pay.reference} maxLength={60} autoCapitalize="characters" onChange={(e) => setPay({ ...pay, reference: e.target.value })} />}
                    </Field>
                  </div>
                  {overpaid > 0 ? (
                    <div className="grid gap-2">
                      <span className="font-bold">They paid {kes(overpaid)} more than the total.</span>
                      <Choice label="Extra money" value={pay.overpay} onChange={(v) => setPay({ ...pay, overpay: v })} options={[{ value: 'refund', label: 'Refund it now' }, { value: 'credit', label: 'Keep as credit' }]} />
                    </div>
                  ) : null}
                  <Check label="Customer wants a receipt" checked={pay.receipt} onChange={(v) => setPay({ ...pay, receipt: v })} />
                </div>
              ) : (
                <div className="grid gap-4">
                  {onTab ? <Notice tone="info">This customer has a running tab. The items go on the tab; print the invoice from their page when you are ready.</Notice> : null}
                  {!onTab ? (
                    <Field label="Due date" optional hint="Leave empty to use their usual payment terms." >
                      {(p) => <Input {...p} type="date" min={todayIso()} value={dueOn} onChange={(e) => setDueOn(e.target.value)} />}
                    </Field>
                  ) : null}
                </div>
              )}
            </Card>
          ) : (
            <Card className="grid gap-4">
              <h2 className="text-[18px]">3. Valid until</h2>
              <Field label="Valid until" optional hint="Leave empty to use the default from Settings.">
                {(p) => <Input {...p} type="date" min={todayIso()} value={validUntil} onChange={(e) => setValidUntil(e.target.value)} />}
              </Field>
            </Card>
          )}
        </div>

        <aside className="grid gap-3 lg:sticky lg:top-6">
          <Card className="grid gap-3">
            <h2 className="text-[18px]">{quotation ? 'Quotation total' : 'Sale total'}</h2>
            <TotalsRows rows={[['Subtotal', totals.subtotal], totals.showVat && [`VAT (${percent}%)`, totals.vat]]} />
            <Band label="Total" amount={totals.total} sub={`${lines.length} ${lines.length === 1 ? 'line' : 'lines'}`} />
            {step === 'review' ? (
              <div className="grid gap-2">
                <Notice tone="info">
                  {quotation
                    ? 'Save the quotation?'
                    : effectivePay === 'now'
                      ? `Save the sale, record ${kes(amount.value || 0)} by ${pay.method === 'mpesa' ? 'M-Pesa' : pay.method === 'cash' ? 'cash' : 'bank'}, and take items off stock?`
                      : onTab ? 'Add these items to the tab and take them off stock?' : 'Issue an invoice on credit and take items off stock?'}
                </Notice>
                <Button onClick={save} loading={busy}>{quotation ? 'Save quotation' : 'Save sale'}</Button>
                <Button variant="secondary" onClick={() => setStep('edit')}>Change something</Button>
              </div>
            ) : (
              <Button onClick={() => check() && setStep('review')}>Review</Button>
            )}
            {Object.keys(errors).length ? <p className="m-0 text-sm text-danger">Fix the fields marked in red first.</p> : null}
          </Card>
        </aside>
      </div>
    </>
  )
}
