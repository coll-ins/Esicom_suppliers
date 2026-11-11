import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, Dialog, Empty, ErrorBox, Field, Input, Loading, PageHeader, dateText, todayIso, useLoad } from '../components/ui'
import { get, post } from '../lib/api'
import { useAuth } from '../lib/auth'
import { kes } from '../lib/money'
import { textError } from '../lib/validate'

export default function Payments() {
  const { me } = useAuth()
  const monthStart = todayIso().slice(0, 8) + '01'
  const [range, setRange] = useState({ from: monthStart, to: todayIso() })
  const [list, error, reload] = useLoad(() => get(`/payments/?from=${range.from}&to=${range.to}`), [range.from, range.to])
  const [voiding, setVoiding] = useState(null)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState(null)

  const act = async (fn) => {
    setBusy(true)
    setActionError(null)
    try {
      await fn()
      setVoiding(null)
      reload()
    } catch (e) {
      setActionError(e)
    } finally {
      setBusy(false)
    }
  }

  const total = (list || []).filter((p) => !p.void && p.method !== 'credit_note').reduce((s, p) => s + p.amount - p.refunded, 0)

  return (
    <>
      <PageHeader title="Payments">Money received. To record a payment, open the customer or the invoice.</PageHeader>
      <div className="mb-5 grid max-w-lg grid-cols-2 gap-4">
        <Field label="From">{(p) => <Input {...p} type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} />}</Field>
        <Field label="To">{(p) => <Input {...p} type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} />}</Field>
      </div>
      <ErrorBox error={error || actionError} onRetry={error ? reload : undefined} />
      {!list && !error ? <Loading /> : null}
      {list && !list.length ? <Empty title="No payments in these dates">Change the dates, or record a payment from a customer's page.</Empty> : null}
      {list?.length ? (
        <>
          <p className="font-bold tnum">Received in this period, after refunds: {kes(total)}</p>
          <ul className="divide-y divide-line overflow-hidden rounded-[var(--radius-card)] border border-line bg-white">
            {list.map((p) => (
              <li key={p.id} className="grid gap-2 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                <div className="min-w-0">
                  <Link to={`/customers/${p.customer.id}`} className="font-bold text-navy underline">{p.customer.name}</Link>
                  <div className="text-sm text-muted">
                    {dateText(p.received_on)}, {p.method_label}{p.reference ? ` ${p.reference}` : ''}
                    {p.allocations.length ? `. Paid ${p.allocations.map((a) => a.number).join(', ')}` : ''}
                    {p.unallocated > 0 ? `. ${kes(p.unallocated)} kept as credit` : ''}
                    {p.refunded > 0 ? `. ${kes(p.refunded)} refunded` : ''}
                    {p.void ? '. Void' : ''}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                  <b className={`tnum ${p.void ? 'text-muted line-through' : ''}`}>{kes(p.amount)}</b>
                  {!p.void && p.method !== 'credit_note' ? (
                    p.receipt
                      ? <Link to={`/documents/${p.receipt.id}`} className="min-h-11 content-center px-2 font-bold text-blue underline">{p.receipt.number}</Link>
                      : p.refunded < p.amount ? <Button variant="secondary" loading={busy} onClick={() => act(() => post(`/payments/${p.id}/receipt/`))}>Make receipt</Button> : null
                  ) : null}
                  {!p.void && me.can_void && p.method !== 'credit_note' && !p.refunded ? (
                    <Button variant="quiet" onClick={() => { setVoiding(p); setReason('') }}>Void</Button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <Dialog open={!!voiding} title="Void this payment?" onClose={() => setVoiding(null)}>
        {voiding ? <p className="m-0">{kes(voiding.amount)} from {voiding.customer.name}. The invoices it paid become unpaid again, and its receipt is voided.</p> : null}
        <ErrorBox error={actionError} />
        <Field label="Reason" hint="Example: M-Pesa reversed." error={reason ? textError(reason, 'Reason', { min: 3, max: 200 }) : ''}>
          {(p) => <Input {...p} value={reason} maxLength={200} onChange={(e) => setReason(e.target.value)} />}
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setVoiding(null)}>Keep it</Button>
          <Button variant="danger" loading={busy} disabled={!!textError(reason, 'Reason', { min: 3, max: 200 })} onClick={() => act(() => post(`/payments/${voiding.id}/void/`, { reason }))}>Void payment</Button>
        </div>
      </Dialog>
    </>
  )
}
