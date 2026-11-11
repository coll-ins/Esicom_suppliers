import { useState } from 'react'
import { Link } from 'react-router-dom'
import { newKey, post } from '../lib/api'
import { kes } from '../lib/money'
import { wholeKes } from '../lib/validate'
import { Band, Button, Check, Choice, ErrorBox, Field, Input, Notice, todayIso } from './ui'

// Record money received from a customer against their open invoices (oldest first).
export default function PaymentForm({ customer, invoices, onDone }) {
  const open = invoices.filter((i) => i.balance > 0 && !i.void)
  const [picked, setPicked] = useState(() => new Set(open.map((i) => i.id)))
  const due = open.filter((i) => picked.has(i.id)).reduce((s, i) => s + i.balance, 0)
  const [f, setF] = useState({ amount: '', method: 'mpesa', reference: '', received_on: todayIso(), overpay: 'refund', receipt: false })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [done, setDone] = useState(null)
  const [saveKey] = useState(newKey)
  const amount = wholeKes(f.amount, 'Amount received', { min: 1 })
  const extra = amount.value ? amount.value - due : 0

  const submit = async (e) => {
    e.preventDefault()
    const errs = {}
    if (amount.error) errs.amount = amount.error
    if (f.method === 'mpesa' && !f.reference.trim()) errs.reference = 'Enter the M-Pesa code, for example TKB7XY12AB.'
    if (open.length && !picked.size) errs.invoices = 'Tick at least one invoice.'
    setErrors(errs)
    if (Object.keys(errs).length) return
    setBusy(true)
    setError(null)
    try {
      const r = await post('/payments/', {
        customer_id: customer.id, amount: amount.value, method: f.method, reference: f.reference.trim(),
        received_on: f.received_on, overpay: f.overpay, receipt: f.receipt,
        invoice_ids: picked.size && picked.size !== open.length ? [...picked] : undefined,
      }, { 'Idempotency-Key': saveKey })
      setDone(r)
      onDone?.(r)
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  if (done) {
    return (
      <div className="grid gap-3">
        <Notice>Recorded {kes(done.amount)} from {customer.name}.{done.overpaid ? ` Extra ${kes(done.overpaid)} ${f.overpay === 'refund' ? 'to refund now' : 'kept as credit'}.` : ''}</Notice>
        {done.receipt ? <Link className="font-bold text-blue underline" to={`/documents/${done.receipt.id}`}>Open receipt {done.receipt.number}</Link> : null}
      </div>
    )
  }

  return (
    <form className="grid gap-4" onSubmit={submit} noValidate>
      <ErrorBox error={error} />
      {open.length ? (
        <fieldset className="grid gap-1">
          <legend className="mb-1 font-bold">Pay these invoices</legend>
          {open.map((i) => (
            <Check
              key={i.id}
              label={`${i.number}: ${kes(i.balance)} left`}
              checked={picked.has(i.id)}
              onChange={(v) => {
                const n = new Set(picked)
                if (v) n.add(i.id); else n.delete(i.id)
                setPicked(n)
              }}
            />
          ))}
          {errors.invoices ? <span className="text-sm text-danger">{errors.invoices}</span> : null}
        </fieldset>
      ) : <Notice tone="info">No unpaid invoices. The money is kept as credit or refunded.</Notice>}
      <Band label="Due on ticked invoices" amount={due} />
      <Choice label="Method" value={f.method} onChange={(v) => setF({ ...f, method: v })} options={[{ value: 'mpesa', label: 'M-Pesa' }, { value: 'cash', label: 'Cash' }, { value: 'bank', label: 'Bank' }]} />
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Amount received (KES)" hint="Whole shillings. Example: 15000." error={errors.amount}>
          {(p) => <Input {...p} inputMode="numeric" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} />}
        </Field>
        <Field label="Date received">
          {(p) => <Input {...p} type="date" max={todayIso()} value={f.received_on} onChange={(e) => setF({ ...f, received_on: e.target.value })} />}
        </Field>
      </div>
      <Field label={f.method === 'mpesa' ? 'M-Pesa code' : 'Reference'} optional={f.method !== 'mpesa'} hint={f.method === 'mpesa' ? 'From the M-Pesa message. Example: TKB7XY12AB.' : 'Cheque or bank slip number, if any.'} error={errors.reference}>
        {(p) => <Input {...p} value={f.reference} maxLength={60} onChange={(e) => setF({ ...f, reference: e.target.value })} />}
      </Field>
      {amount.value && amount.value < due ? (
        <Notice tone="warn">This is less than the amount due. It is accepted only if part payments are allowed for this customer or invoice.</Notice>
      ) : null}
      {extra > 0 ? (
        <div className="grid gap-2">
          <span className="font-bold">{kes(extra)} more than what is due.</span>
          <Choice label="Extra money" value={f.overpay} onChange={(v) => setF({ ...f, overpay: v })} options={[{ value: 'refund', label: 'Refund it' }, { value: 'credit', label: 'Keep as credit' }]} />
        </div>
      ) : null}
      <Check label="Make a receipt" checked={f.receipt} onChange={(v) => setF({ ...f, receipt: v })} />
      <Button type="submit" loading={busy}>Record payment</Button>
    </form>
  )
}
