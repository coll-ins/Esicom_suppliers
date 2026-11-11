import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import PaymentForm from '../components/PaymentForm'
import Share from '../components/Share'
import {
  BackLink, Band, Button, ButtonLink, Card, Dialog, ErrorBox, Field, Input, Loading, Notice, PageHeader, Pill, Table,
  TotalsRows, dateText, useLoad,
} from '../components/ui'
import { get, patch, post } from '../lib/api'
import { useAuth } from '../lib/auth'
import { kes, num } from '../lib/money'
import { textError } from '../lib/validate'

export default function DocumentView() {
  const { id } = useParams()
  const { me } = useAuth()
  const navigate = useNavigate()
  const [doc, error, reload] = useLoad(() => get(`/documents/${id}/`), [id])
  const [dialog, setDialog] = useState(null) // void | pay | etims
  const [reason, setReason] = useState('')
  const [etims, setEtims] = useState('')
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState(null)

  const act = async (fn) => {
    setBusy(true)
    setActionError(null)
    try {
      await fn()
      setDialog(null)
      reload()
    } catch (e) {
      setActionError(e)
    } finally {
      setBusy(false)
    }
  }

  if (error) return <><BackLink to="/documents" label="documents" /><ErrorBox error={error} onRetry={reload} /></>
  if (!doc) return <Loading />

  const isInv = doc.type === 'INV'
  const owner = me.role === 'owner'
  const reasonErr = textError(reason, 'Reason', { min: 3, max: 200 })

  return (
    <>
      <PageHeader
        back={<BackLink to="/documents" label="documents" />}
        title={doc.number}
        actions={<Pill status={doc.status} />}
      >
        {doc.type_label} for <Link className="font-bold text-blue underline" to={`/customers/${doc.customer.id}`}>{doc.customer.name}</Link>, issued {dateText(doc.issued_on)}
        {doc.due_on ? `, ${doc.type === 'QTN' ? 'valid until' : 'due'} ${dateText(doc.due_on)}` : ''}
      </PageHeader>

      {doc.void ? <Notice tone="warn">Void: {doc.void_reason}. The number stays used and is never reissued.</Notice> : null}
      <ErrorBox error={actionError} />

      <div className="mt-4 grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start">
        <div className="grid gap-6">
          <ul className="grid gap-2 sm:hidden">
            {doc.lines.map((l, i) => (
              <li key={i} className="rounded-[var(--radius-control)] border border-line bg-white px-4 py-3">
                <div className="font-bold">{l.description}</div>
                <div className="flex justify-between gap-3 text-[15px]">
                  <span className="text-muted tnum">{num(l.qty)} x {kes(l.unit_price)}{l.vat_exempt && doc.type !== 'RCP' ? ', VAT exempt' : ''}</span>
                  <b className="tnum">{kes(l.amount)}</b>
                </div>
              </li>
            ))}
          </ul>
          <div className="hidden sm:block">
          <Table head={['#', 'Item description', { label: 'Qty', right: true }, { label: 'Unit price (KES)', right: true }, { label: 'Total (KES)', right: true }]}>
            {doc.lines.map((l, i) => (
              <tr key={i}>
                <td className="text-muted">{i + 1}</td>
                <td>{l.description}{l.vat_exempt && doc.type !== 'RCP' ? <span className="text-sm text-muted"> (VAT exempt)</span> : null}</td>
                <td className="text-right tnum">{num(l.qty)}</td>
                <td className="text-right tnum">{num(l.unit_price)}</td>
                <td className="text-right tnum">{num(l.amount)}</td>
              </tr>
            ))}
          </Table>
          </div>

          {doc.related || doc.children.length ? (
            <Card className="grid gap-2">
              <h2 className="text-[18px]">Linked documents</h2>
              {doc.related ? <Link className="font-bold text-blue underline" to={`/documents/${doc.related.id}`}>{doc.related.number}</Link> : null}
              {doc.children.map((c) => (
                <Link key={c.id} className="font-bold text-blue underline" to={`/documents/${c.id}`}>{c.number}{c.void ? ' (void)' : ''}</Link>
              ))}
            </Card>
          ) : null}

          {isInv ? (
            <Card className="grid gap-3">
              <h2 className="text-[18px]">Payments</h2>
              {doc.payments.length ? (
                <ul className="grid gap-1">
                  {doc.payments.map((p, i) => (
                    <li key={i} className="flex justify-between gap-3 rounded-md bg-pale px-3 py-2">
                      <span>{dateText(p.received_on)}, {p.method}{p.reference ? ` ${p.reference}` : ''}</span>
                      <b className="tnum">{kes(p.amount)}</b>
                    </li>
                  ))}
                </ul>
              ) : <p className="m-0 text-muted">No payments yet.</p>}
            </Card>
          ) : null}
        </div>

        <aside className="grid gap-4 lg:sticky lg:top-6">
          <Card className="grid gap-3">
            <TotalsRows rows={[
              ['Subtotal', doc.subtotal],
              doc.lines.some((l) => !l.vat_exempt) && [`VAT (${doc.vat_percent}%)`, doc.vat],
              isInv && doc.total !== doc.balance && !doc.void && ['Paid or credited', doc.total - doc.balance],
            ]} />
            <Band label={isInv && !doc.void ? (doc.balance > 0 ? 'Balance due' : 'Paid in full') : 'Total'} amount={isInv && !doc.void ? doc.balance : doc.total} />
          </Card>

          {!doc.void ? (
            <Card className="grid gap-3">
              <h2 className="text-[18px]">Send</h2>
              <Share doc={doc} />
            </Card>
          ) : null}

          {!doc.void ? (
            <Card className="grid gap-2">
              <h2 className="text-[18px]">Actions</h2>
              {isInv && doc.balance > 0 ? <Button onClick={() => setDialog('pay')}>Record payment</Button> : null}
              {doc.type === 'QTN' && !doc.children.some((c) => c.type === 'INV' && !c.void) ? (
                <Button loading={busy} onClick={() => act(async () => {
                  const inv = await post(`/documents/${doc.id}/convert/`)
                  navigate(`/documents/${inv.id}`)
                })}>Turn into invoice</Button>
              ) : null}
              {isInv ? <ButtonLink to={`/documents/${doc.id}/credit-note`}>Issue credit note</ButtonLink> : null}
              {isInv ? (
                <Button variant="secondary" onClick={() => { setEtims(doc.etims_number); setDialog('etims') }}>
                  {doc.etims_number ? `eTIMS number: ${doc.etims_number}` : 'Add eTIMS number'}
                </Button>
              ) : null}
              {isInv && owner && doc.balance > 0 ? (
                <Button variant="secondary" loading={busy} onClick={() => act(() => patch(`/documents/${doc.id}/update/`, { allow_partial: !doc.partial_allowed }))}>
                  {doc.partial_allowed ? 'Stop part payments on this invoice' : 'Allow part payments on this invoice'}
                </Button>
              ) : null}
              {me.can_void ? <Button variant="danger" onClick={() => { setReason(''); setDialog('void') }}>Void {doc.type_label.toLowerCase()}</Button> : null}
            </Card>
          ) : null}
        </aside>
      </div>

      <Dialog open={dialog === 'void'} title={`Void ${doc.number}?`} onClose={() => setDialog(null)}>
        <p className="m-0 text-muted">
          {isInv ? 'Stock on its lines goes back on the shelf. Money already paid stays with the customer as credit.' : 'The number stays used.'} This cannot be undone.
        </p>
        <ErrorBox error={actionError} />
        <Field label="Reason" hint="Example: Customer cancelled the order." error={reason ? reasonErr : ''}>
          {(p) => <Input {...p} value={reason} maxLength={200} onChange={(e) => setReason(e.target.value)} />}
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDialog(null)}>Keep it</Button>
          <Button variant="danger" loading={busy} disabled={!!reasonErr} onClick={() => act(() => post(`/documents/${doc.id}/void/`, { reason }))}>Void it</Button>
        </div>
      </Dialog>

      <Dialog open={dialog === 'etims'} title="eTIMS number" onClose={() => setDialog(null)}>
        <p className="m-0 text-muted">The number from the KRA portal for this invoice. It does not change any amounts.</p>
        <Field label="eTIMS number" hint="Example: 0040123456789">
          {(p) => <Input {...p} value={etims} maxLength={40} onChange={(e) => setEtims(e.target.value)} />}
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDialog(null)}>Cancel</Button>
          <Button loading={busy} onClick={() => act(() => patch(`/documents/${doc.id}/update/`, { etims_number: etims }))}>Save</Button>
        </div>
      </Dialog>

      <Dialog open={dialog === 'pay'} title={`Payment from ${doc.customer.name}`} onClose={() => { setDialog(null); reload() }}>
        {dialog === 'pay' ? (
          <PaymentForm
            customer={doc.customer}
            invoices={[{ id: doc.id, number: doc.number, balance: doc.balance }]}
          />
        ) : null}
      </Dialog>
    </>
  )
}
