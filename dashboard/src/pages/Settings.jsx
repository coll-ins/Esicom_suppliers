import { useState } from 'react'
import { Button, Card, Check, Dialog, ErrorBox, Field, Input, Loading, Notice, PageHeader, PasswordInput, useLoad } from '../components/ui'
import { get, post, put } from '../lib/api'
import { useAuth } from '../lib/auth'
import { emailError, textError, wholeQty } from '../lib/validate'

const TEXT = [
  ['kra_pin', 'KRA PIN', 'Printed on every document when filled. Example: P051234567X.', 20],
  ['mpesa_paybill', 'M-Pesa paybill', 'Digits only. Example: 247247.', 10],
  ['mpesa_account', 'Paybill account', 'What customers type as the account. Example: their invoice number or "ESICOM".', 40],
  ['mpesa_till', 'M-Pesa till (Buy Goods)', 'Digits only. Example: 5123456.', 10],
  ['bank_name', 'Bank name', 'Example: Equity Bank.', 80],
  ['bank_branch', 'Bank branch', 'Example: Kenyatta Avenue.', 80],
  ['bank_account_name', 'Account name', 'Example: Esicom Suppliers Ltd.', 120],
  ['bank_account_number', 'Account number', 'Example: 0123456789012.', 40],
]

function BusinessSettings() {
  const { refresh } = useAuth()
  const [s, error, reload] = useLoad(() => get('/settings/'))
  const [f, setF] = useState(null)
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [saveError, setSaveError] = useState(null)
  const [saved, setSaved] = useState(false)
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (!s) return <Loading />
  const v = f || s
  const set = (k) => (e) => { setF({ ...v, [k]: e.target.value }); setSaved(false) }

  const save = async () => {
    const e = {}
    if (v.mpesa_paybill && !/^\d+$/.test(v.mpesa_paybill)) e.mpesa_paybill = 'Digits only, for example 247247.'
    if (v.mpesa_till && !/^\d+$/.test(v.mpesa_till)) e.mpesa_till = 'Digits only, for example 5123456.'
    for (const [k, label, , max] of TEXT) { const t = textError(v[k], label, { max }); if (t) e[k] = t }
    const vat = wholeQty(v.vat_percent, 'VAT %', { min: 0 }); if (vat.error) e.vat_percent = vat.error
    const terms = wholeQty(v.payment_terms_days, 'Payment terms', { min: 0 }); if (terms.error) e.payment_terms_days = terms.error
    const valid = wholeQty(v.quotation_valid_days, 'Quotation valid', { min: 1 }); if (valid.error) e.quotation_valid_days = valid.error
    setErrors(e)
    if (Object.keys(e).length) return
    setBusy(true)
    setSaveError(null)
    try {
      await put('/settings/', v)
      setF(null)
      setSaved(true)
      reload()
      refresh()
    } catch (err) {
      setSaveError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card className="grid gap-5">
      <h2 className="text-[20px]">Business details</h2>
      <p className="m-0 text-muted">Empty fields are never printed. Fill these when you have them; nothing is invented.</p>
      <ErrorBox error={saveError} />
      <div className="grid gap-4 sm:grid-cols-2">
        {TEXT.map(([k, label, hint, max]) => (
          <Field key={k} label={label} optional hint={hint} error={errors[k]}>
            {(p) => <Input {...p} value={v[k]} maxLength={max} onChange={set(k)} />}
          </Field>
        ))}
      </div>
      <h3 className="mt-2 text-[17px]">Money rules</h3>
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="VAT %" hint="Kenya standard rate is 16. Changes new documents only." error={errors.vat_percent}>
          {(p) => <Input {...p} inputMode="numeric" value={v.vat_percent} onChange={set('vat_percent')} />}
        </Field>
        <Field label="Payment terms (days)" hint="Due date for credit invoices. Example: 30." error={errors.payment_terms_days}>
          {(p) => <Input {...p} inputMode="numeric" value={v.payment_terms_days} onChange={set('payment_terms_days')} />}
        </Field>
        <Field label="Quotations valid (days)" hint="Example: 14." error={errors.quotation_valid_days}>
          {(p) => <Input {...p} inputMode="numeric" value={v.quotation_valid_days} onChange={set('quotation_valid_days')} />}
        </Field>
      </div>
      <h3 className="mt-2 text-[17px]">What staff may do</h3>
      <Check label="Staff can void documents and payments" hint="Off: only you can void." checked={v.staff_can_void} onChange={(x) => { setF({ ...v, staff_can_void: x }); setSaved(false) }} />
      <Check label="Staff can set VAT exempt on products" checked={v.staff_can_set_vat_exempt} onChange={(x) => { setF({ ...v, staff_can_set_vat_exempt: x }); setSaved(false) }} />
      {saved ? <Notice>Settings saved.</Notice> : null}
      <Button className="justify-self-start" loading={busy} disabled={!f} onClick={save}>Save settings</Button>
    </Card>
  )
}

function Users() {
  const { me } = useAuth()
  const [list, error, reload] = useLoad(() => get('/users/'))
  const [adding, setAdding] = useState(false)
  const [f, setF] = useState({ name: '', email: '', password: '' })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState(null)

  const act = async (fn) => {
    setBusy(true)
    setActionError(null)
    try { await fn(); setAdding(false); reload() } catch (e) { setActionError(e) } finally { setBusy(false) }
  }
  const add = () => {
    const e = {
      name: textError(f.name, 'Name', { min: 2, max: 150 }),
      email: emailError(f.email) || (!f.email.trim() ? 'Email is required.' : ''),
      password: f.password.length < 8 ? 'At least 8 characters.' : '',
    }
    const bad = Object.fromEntries(Object.entries(e).filter(([, x]) => x))
    setErrors(bad)
    if (!Object.keys(bad).length) act(() => post('/users/', f))
  }

  return (
    <Card className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-[20px]">Staff</h2>
        <Button onClick={() => { setF({ name: '', email: '', password: '' }); setErrors({}); setAdding(true) }}>Add staff member</Button>
      </div>
      <ErrorBox error={error || actionError} onRetry={error ? reload : undefined} />
      {!list && !error ? <Loading /> : null}
      <ul className="grid gap-2">
        {(list || []).map((u) => (
          <li key={u.id} className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-control)] border border-line px-4 py-3">
            <span><b>{u.name}</b><span className="block text-sm text-muted">{u.email}, {u.role === 'owner' ? 'Owner' : 'Staff'}{u.active ? '' : ', removed'}</span></span>
            {u.role !== 'owner' && u.id !== me.id ? (
              u.active
                ? <Button variant="danger" loading={busy} onClick={() => window.confirm(`Remove ${u.name}? They are logged out on every device.`) && act(() => post(`/users/${u.id}/remove/`))}>Remove</Button>
                : <Button variant="secondary" loading={busy} onClick={() => act(() => post(`/users/${u.id}/restore/`))}>Restore</Button>
            ) : null}
          </li>
        ))}
      </ul>
      <Dialog open={adding} title="Add staff member" onClose={() => setAdding(false)}>
        <p className="m-0 text-muted">Staff can sell, take payments, manage customers and stock. They cannot see cost or profit, change settings, manage staff, or void unless you allow it.</p>
        <ErrorBox error={actionError} />
        <Field label="Full name" hint="Example: Jane Wanjiku." error={errors.name}>{(p) => <Input {...p} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />}</Field>
        <Field label="Email" hint="They log in with this. Example: jane@gmail.com." error={errors.email}>{(p) => <Input {...p} type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />}</Field>
        <Field label="Starting password" hint="At least 8 characters, not only numbers. Tell them in person; they can change it." error={errors.password}>{(p) => <Input {...p} type="text" autoComplete="off" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} />}</Field>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setAdding(false)}>Cancel</Button>
          <Button loading={busy} onClick={add}>Add</Button>
        </div>
      </Dialog>
    </Card>
  )
}

export function MyAccount() {
  const { logoutEverywhere } = useAuth()
  const [f, setF] = useState({ current: '', new: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [done, setDone] = useState(false)
  const change = async () => {
    setBusy(true); setError(null); setDone(false)
    try { await post('/auth/password/', f); setDone(true); setF({ current: '', new: '' }) } catch (e) { setError(e) } finally { setBusy(false) }
  }
  return (
    <Card className="grid gap-4">
      <h2 className="text-[20px]">My account</h2>
      <ErrorBox error={error} />
      {done ? <Notice>Password changed. Other devices are logged out.</Notice> : null}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Current password">{(p) => <PasswordInput {...p} autoComplete="current-password" value={f.current} onChange={(e) => setF({ ...f, current: e.target.value })} />}</Field>
        <Field label="New password" hint="At least 8 characters, not only numbers.">{(p) => <PasswordInput {...p} autoComplete="new-password" value={f.new} onChange={(e) => setF({ ...f, new: e.target.value })} />}</Field>
      </div>
      <Button className="justify-self-start" loading={busy} disabled={!f.current || !f.new} onClick={change}>Change password</Button>
      <div className="border-t border-line pt-4">
        <p className="mt-0 text-muted">Lost a phone or laptop? This logs you out on every device, including this one.</p>
        <Button variant="danger" onClick={() => window.confirm('Log out on every device?') && logoutEverywhere()}>Log out everywhere</Button>
      </div>
    </Card>
  )
}

export default function Settings() {
  return (
    <>
      <PageHeader title="Settings" />
      <div className="grid max-w-4xl gap-6">
        <BusinessSettings />
        <Users />
        <MyAccount />
      </div>
    </>
  )
}
