import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import PaymentForm from '../components/PaymentForm'
import {
  BackLink, Band, Button, ButtonLink, Card, Check, Choice, Dialog, Empty, ErrorBox, Field, Input, Loading, Notice,
  PageHeader, Pill, TotalsRows, dateText, todayIso, useLoad,
} from '../components/ui'
import { get, patch, post, postForPdf } from '../lib/api'
import { useAuth } from '../lib/auth'
import { kes, saleTotals } from '../lib/money'
import { PHONE_HELP, emailError, phoneError, textError, wholeKes } from '../lib/validate'

function firstOfMonth() {
  return todayIso().slice(0, 8) + '01'
}

export default function CustomerView() {
  const { id } = useParams()
  const { me } = useAuth()
  const owner = me.role === 'owner'
  const [c, error, reload] = useLoad(() => get(`/customers/${id}/`), [id])
  const [dialog, setDialog] = useState(null) // edit | pay | statement | refund | removeLine
  const [form, setForm] = useState({})
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState(null)
  const [notice, setNotice] = useState('')
  const [period, setPeriod] = useState({ from: firstOfMonth(), to: todayIso() })
  const [refund, setRefund] = useState({ amount: '', note: '' })
  const [line, setLine] = useState(null)
  const [reason, setReason] = useState('')

  const act = async (fn, after) => {
    setBusy(true)
    setActionError(null)
    try {
      const r = await fn()
      setDialog(null)
      if (after) after(r)
      reload()
    } catch (e) {
      setActionError(e)
    } finally {
      setBusy(false)
    }
  }

  if (error) return <><BackLink to="/customers" label="customers" /><ErrorBox error={error} onRetry={reload} /></>
  if (!c) return <Loading />

  const b = c.balance
  const tabTotals = saleTotals(c.tab_lines.map((l) => ({ qty: l.qty, unitPrice: l.unit_price, vatExempt: l.vat_exempt })), me.vat_percent)

  const openEdit = () => {
    setForm({
      name: c.name, phone: c.phone, email: c.email, address: c.address, kra_pin: c.kra_pin, billing: c.billing,
      allow_partial: c.allow_partial, credit_limit: c.credit_limit ?? '', payment_terms_days: c.payment_terms_days ?? '',
    })
    setErrors({})
    setDialog('edit')
  }
  const saveEdit = () => {
    const e = {
      name: textError(form.name, 'Name', { min: 2, max: 160 }),
      phone: phoneError(form.phone),
      email: emailError(form.email),
      credit_limit: form.credit_limit === '' ? '' : wholeKes(form.credit_limit, 'Credit limit').error || '',
    }
    const bad = Object.fromEntries(Object.entries(e).filter(([, v]) => v))
    setErrors(bad)
    if (Object.keys(bad).length) return
    const body = { name: form.name, phone: form.phone, email: form.email, address: form.address, kra_pin: form.kra_pin, billing: form.billing }
    if (owner) Object.assign(body, { allow_partial: form.allow_partial, credit_limit: form.credit_limit, payment_terms_days: form.payment_terms_days })
    act(() => patch(`/customers/${c.id}/`, body))
  }

  const statement = async (email) => {
    setBusy(true)
    setActionError(null)
    try {
      if (email) {
        const r = await post(`/customers/${c.id}/statement/`, { ...period, email: true })
        setNotice(r.detail)
        setDialog(null)
      } else {
        const url = await postForPdf(`/customers/${c.id}/statement/`, period)
        window.open(url, '_blank', 'noopener')
      }
    } catch (e) {
      setActionError(e)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader
        back={<BackLink to="/customers" label="customers" />}
        title={c.name}
        actions={<>
          <ButtonLink to="/sell">Record a sale</ButtonLink>
          <Button variant="secondary" onClick={openEdit}>Edit details</Button>
        </>}
      >
        {[c.phone, c.email, c.address].filter(Boolean).join(', ') || 'No contact details yet.'}
      </PageHeader>
      {notice ? <Notice>{notice}</Notice> : null}
      <ErrorBox error={actionError} />

      <div className="mt-4 grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start">
        <div className="grid gap-6">
          {c.billing === 'tab' ? (
            <Card className="grid gap-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-[18px]">Running tab</h2>
                <span className="text-sm text-muted">{c.tab_open ? 'Open' : 'No open tab. A new one opens with the next sale.'}</span>
              </div>
              {c.tab_lines.length ? (
                <>
                  <ul className="grid gap-1">
                    {c.tab_lines.map((l) => (
                      <li key={l.id} className="flex items-center justify-between gap-3 rounded-md bg-pale px-3 py-2">
                        <span className="min-w-0"><b>{l.qty} x {l.description}</b><span className="block text-sm text-muted">{dateText(l.created_at)}, {kes(l.unit_price)} each</span></span>
                        {me.can_void ? <Button variant="quiet" onClick={() => { setLine(l); setReason(''); setDialog('removeLine') }}>Remove</Button> : null}
                      </li>
                    ))}
                  </ul>
                  <Band label="Not yet invoiced" amount={tabTotals.total} sub="Including VAT" />
                </>
              ) : <p className="m-0 text-muted">Nothing waiting. Every item on the tab is already invoiced.</p>}
              <div className="flex flex-wrap gap-2">
                <Button disabled={!c.tab_lines.length} loading={busy} onClick={() => act(() => post(`/customers/${c.id}/tab/bill/`), (inv) => setNotice(`Invoice ${inv.number} printed for ${kes(inv.total)}. The tab stays open.`))}>
                  Print invoice now
                </Button>
                {c.tab_open ? (
                  <Button variant="secondary" loading={busy} onClick={() => window.confirm('Close the tab? Unbilled items go on a final invoice.') && act(() => post(`/customers/${c.id}/tab/close/`), (r) => setNotice(r.invoice ? `Tab closed. Final invoice ${r.invoice.number}.` : 'Tab closed.'))}>
                    Close tab
                  </Button>
                ) : null}
              </div>
            </Card>
          ) : null}

          <Card className="grid gap-3 p-0">
            <h2 className="px-5 pt-4 text-[18px]">Invoices</h2>
            {c.invoices.length ? (
              <ul className="divide-y divide-line">
                {c.invoices.map((d) => (
                  <li key={d.id}>
                    <Link to={`/documents/${d.id}`} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-5 py-3 hover:bg-paper">
                      <span><b>{d.number}</b><span className="block text-sm text-muted">{dateText(d.issued_on)}{d.due_on ? `, due ${dateText(d.due_on)}` : ''}</span></span>
                      <span className="grid justify-items-end gap-1 tnum"><b>{kes(d.balance > 0 ? d.balance : d.total)}</b><Pill status={d.status} /></span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : <div className="px-5 pb-5"><Empty title="No invoices yet" /></div>}
          </Card>

          {c.documents.length ? (
            <Card className="grid gap-3 p-0">
              <h2 className="px-5 pt-4 text-[18px]">Quotations, receipts and credit notes</h2>
              <ul className="divide-y divide-line">
                {c.documents.map((d) => (
                  <li key={d.id}>
                    <Link to={`/documents/${d.id}`} className="flex justify-between gap-3 px-5 py-3 hover:bg-paper">
                      <span><b>{d.number}</b><span className="block text-sm text-muted">{d.type_label}, {dateText(d.issued_on)}</span></span>
                      <span className="grid justify-items-end gap-1 tnum">{kes(d.total)}<Pill status={d.status} /></span>
                    </Link>
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}

          <Card className="grid gap-3 p-0">
            <h2 className="px-5 pt-4 text-[18px]">Payments</h2>
            {c.payments.length ? (
              <ul className="divide-y divide-line">
                {c.payments.map((p) => (
                  <li key={p.id} className="flex justify-between gap-3 px-5 py-3">
                    <span><b>{p.method_label}{p.reference ? ` ${p.reference}` : ''}</b><span className="block text-sm text-muted">{dateText(p.received_on)}{p.void ? ', void' : ''}{p.refunded ? `, ${kes(p.refunded)} refunded` : ''}</span></span>
                    <b className={`tnum ${p.void ? 'text-muted line-through' : ''}`}>{kes(p.amount)}</b>
                  </li>
                ))}
              </ul>
            ) : <p className="m-0 px-5 pb-5 text-muted">No payments yet.</p>}
          </Card>
        </div>

        <aside className="grid gap-4 lg:sticky lg:top-6">
          <Card className="grid gap-3">
            <TotalsRows rows={[['Unpaid invoices', b.owed], b.unbilled > 0 && ['On tab, not invoiced', b.unbilled], b.credit > 0 && ['Credit in their favour', b.credit]]} />
            <Band label={b.balance >= 0 ? 'Balance owed' : 'In their favour'} amount={Math.abs(b.balance)} sub={c.credit_limit !== null ? `Credit limit ${kes(c.credit_limit)}` : 'No credit limit'} />
            <Button onClick={() => setDialog('pay')}>Record payment</Button>
            <Button variant="secondary" onClick={() => setDialog('statement')}>Statement</Button>
            {owner && b.credit > 0 ? <Button variant="secondary" onClick={() => { setRefund({ amount: String(b.credit), note: '' }); setDialog('refund') }}>Refund credit</Button> : null}
          </Card>
          <Card className="grid gap-1 text-[15px]">
            <div><b>Billing:</b> {c.billing === 'tab' ? 'Running tab' : 'One invoice per sale'}</div>
            <div><b>Part payments:</b> {c.allow_partial ? 'Allowed' : 'Not allowed'}</div>
            <div><b>Payment terms:</b> {c.payment_terms_days ?? 'Default'}{c.payment_terms_days !== null ? ' days' : ''}</div>
            {c.kra_pin ? <div><b>KRA PIN:</b> {c.kra_pin}</div> : null}
          </Card>
        </aside>
      </div>

      <Dialog open={dialog === 'pay'} title={`Payment from ${c.name}`} onClose={() => { setDialog(null); reload() }}>
        {dialog === 'pay' ? <PaymentForm customer={c} invoices={c.invoices} /> : null}
      </Dialog>

      <Dialog open={dialog === 'statement'} title="Statement" onClose={() => setDialog(null)}>
        <p className="m-0 text-muted">Invoices, credit notes, payments and refunds in the period, with a running balance.</p>
        <ErrorBox error={actionError} />
        <div className="grid grid-cols-2 gap-4">
          <Field label="From">{(p) => <Input {...p} type="date" value={period.from} onChange={(e) => setPeriod({ ...period, from: e.target.value })} />}</Field>
          <Field label="To">{(p) => <Input {...p} type="date" value={period.to} onChange={(e) => setPeriod({ ...period, to: e.target.value })} />}</Field>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="secondary" loading={busy} onClick={() => statement(false)}>Open PDF</Button>
          <Button loading={busy} disabled={!c.email} onClick={() => statement(true)}>{c.email ? `Email to ${c.email}` : 'No email saved'}</Button>
        </div>
      </Dialog>

      <Dialog open={dialog === 'refund'} title="Refund credit" onClose={() => setDialog(null)}>
        <ErrorBox error={actionError} />
        <Field label="Amount (KES)" hint={`Up to ${kes(b.credit)}.`}>
          {(p) => <Input {...p} inputMode="numeric" value={refund.amount} onChange={(e) => setRefund({ ...refund, amount: e.target.value })} />}
        </Field>
        <Field label="How it was refunded" hint="Example: Cash at the counter, or M-Pesa code TKB7XY12AB.">
          {(p) => <Input {...p} value={refund.note} maxLength={200} onChange={(e) => setRefund({ ...refund, note: e.target.value })} />}
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDialog(null)}>Cancel</Button>
          <Button loading={busy} onClick={() => act(() => post(`/customers/${c.id}/refund/`, { amount: refund.amount, note: refund.note }))}>Record refund</Button>
        </div>
      </Dialog>

      <Dialog open={dialog === 'removeLine'} title="Remove from tab?" onClose={() => setDialog(null)}>
        {line ? <p className="m-0">{line.qty} x {line.description}. Stock goes back on the shelf.</p> : null}
        <ErrorBox error={actionError} />
        <Field label="Reason" hint="Example: Added by mistake.">
          {(p) => <Input {...p} value={reason} maxLength={200} onChange={(e) => setReason(e.target.value)} />}
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDialog(null)}>Keep it</Button>
          <Button variant="danger" loading={busy} onClick={() => act(() => post(`/tab-lines/${line.id}/remove/`, { reason }))}>Remove</Button>
        </div>
      </Dialog>

      <Dialog open={dialog === 'edit'} title="Edit customer" onClose={() => setDialog(null)}>
        <ErrorBox error={actionError} />
        <Field label="Name" error={errors.name}>{(p) => <Input {...p} value={form.name || ''} maxLength={160} onChange={(e) => setForm({ ...form, name: e.target.value })} />}</Field>
        <Field label="Phone" optional hint={PHONE_HELP} error={errors.phone}>{(p) => <Input {...p} type="tel" value={form.phone || ''} onChange={(e) => setForm({ ...form, phone: e.target.value })} />}</Field>
        <Field label="Email" optional hint="Example: accounts@company.co.ke" error={errors.email}>{(p) => <Input {...p} type="email" value={form.email || ''} onChange={(e) => setForm({ ...form, email: e.target.value })} />}</Field>
        <Field label="Address" optional hint="Example: Westlands, Nairobi">{(p) => <Input {...p} value={form.address || ''} maxLength={200} onChange={(e) => setForm({ ...form, address: e.target.value })} />}</Field>
        <Field label="Customer KRA PIN" optional hint="Example: P051234567X. Printed on their invoices.">{(p) => <Input {...p} value={form.kra_pin || ''} maxLength={20} onChange={(e) => setForm({ ...form, kra_pin: e.target.value.toUpperCase() })} />}</Field>
        <div className="grid gap-1.5">
          <span className="font-bold">Billing</span>
          <Choice label="Billing" value={form.billing} onChange={(v) => setForm({ ...form, billing: v })} options={[{ value: 'per_sale', label: 'Invoice per sale' }, { value: 'tab', label: 'Running tab' }]} />
        </div>
        {owner ? (
          <>
            <Check label="Allow part payments" hint="Off: each invoice must be paid in full." checked={form.allow_partial} onChange={(v) => setForm({ ...form, allow_partial: v })} />
            <Field label="Credit limit (KES)" optional hint="Leave empty for no limit. You and staff get an alert when they go over." error={errors.credit_limit}>
              {(p) => <Input {...p} inputMode="numeric" value={form.credit_limit} onChange={(e) => setForm({ ...form, credit_limit: e.target.value })} />}
            </Field>
            <Field label="Payment terms (days)" optional hint="Leave empty to use the default from Settings. Example: 30.">
              {(p) => <Input {...p} inputMode="numeric" value={form.payment_terms_days} onChange={(e) => setForm({ ...form, payment_terms_days: e.target.value })} />}
            </Field>
          </>
        ) : null}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDialog(null)}>Cancel</Button>
          <Button loading={busy} onClick={saveEdit}>Save</Button>
        </div>
      </Dialog>
    </>
  )
}
