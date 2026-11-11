import { useEffect, useMemo, useState } from 'react'
import { get } from '../lib/api'
import { kes } from '../lib/money'
import { PHONE_HELP, emailError, phoneError, textError } from '../lib/validate'
import { Button, Choice, Field, Input, Pill } from './ui'

function useDebounced(value, ms = 250) {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return v
}

export const emptyNewCustomer = { name: '', phone: '', email: '', billing: 'per_sale' }

export function newCustomerErrors(c) {
  return {
    name: textError(c.name, 'Customer name', { min: 2, max: 160 }),
    phone: phoneError(c.phone),
    email: emailError(c.email),
  }
}

// value: null | { kind: 'existing', customer } | { kind: 'walkin' } | { kind: 'new', fields }
export function CustomerPicker({ value, onChange, allowWalkIn = true, errors = {} }) {
  const [q, setQ] = useState('')
  const dq = useDebounced(q)
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (value) return
    let live = true
    setLoading(true)
    get(`/customers/?q=${encodeURIComponent(dq)}`)
      .then((r) => live && setResults(r.slice(0, 8)))
      .catch(() => live && setResults([]))
      .finally(() => live && setLoading(false))
    return () => { live = false }
  }, [dq, value])

  if (value?.kind === 'existing') {
    const c = value.customer
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-control)] border border-blue bg-pale px-4 py-3">
        <div>
          <div className="font-bold">{c.name}</div>
          <div className="text-sm text-muted">
            {[c.phone, c.billing === 'tab' ? 'Running tab' : 'Invoice per sale'].filter(Boolean).join(', ')}
            {c.balance?.balance > 0 ? `. Owes ${kes(c.balance.balance)}` : ''}
          </div>
        </div>
        <Button variant="secondary" onClick={() => onChange(null)}>Change</Button>
      </div>
    )
  }
  if (value?.kind === 'walkin') {
    return (
      <div className="flex items-center justify-between gap-3 rounded-[var(--radius-control)] border border-blue bg-pale px-4 py-3">
        <div><div className="font-bold">Walk-in customer</div><div className="text-sm text-muted">Pays now. No account kept.</div></div>
        <Button variant="secondary" onClick={() => onChange(null)}>Change</Button>
      </div>
    )
  }
  if (value?.kind === 'new') {
    const f = value.fields
    const set = (k) => (e) => onChange({ kind: 'new', fields: { ...f, [k]: e.target.value } })
    return (
      <div className="grid gap-4 rounded-[var(--radius-control)] border border-line bg-white p-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-[17px]">New customer</h3>
          <Button variant="quiet" onClick={() => onChange(null)}>Search instead</Button>
        </div>
        <Field label="Name" hint="Person or company. Example: Nairobi Hospital Procurement." error={errors.name}>
          {(p) => <Input {...p} value={f.name} onChange={set('name')} autoComplete="off" maxLength={160} />}
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Phone" optional hint={PHONE_HELP} error={errors.phone}>
            {(p) => <Input {...p} type="tel" inputMode="tel" value={f.phone} onChange={set('phone')} />}
          </Field>
          <Field label="Email" optional hint="For emailing invoices. Example: accounts@company.co.ke." error={errors.email}>
            {(p) => <Input {...p} type="email" inputMode="email" value={f.email} onChange={set('email')} />}
          </Field>
        </div>
        <div className="grid gap-1.5">
          <span className="text-[15px] font-bold">How do they pay?</span>
          <Choice
            label="Billing"
            value={f.billing}
            onChange={(v) => onChange({ kind: 'new', fields: { ...f, billing: v } })}
            options={[{ value: 'per_sale', label: 'Invoice per sale' }, { value: 'tab', label: 'Running tab' }]}
          />
          <span className="text-sm text-muted">Running tab: items add up and you print the invoice when you want.</span>
        </div>
      </div>
    )
  }
  return (
    <div className="grid gap-3">
      <Field label="Find customer" hint="Type a name, phone or email." error={errors.customer}>
        {(p) => <Input {...p} type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Example: Acme" autoComplete="off" />}
      </Field>
      <ul className="grid gap-1" aria-busy={loading}>
        {results.map((c) => (
          <li key={c.id}>
            <button type="button" onClick={() => onChange({ kind: 'existing', customer: c })} className="flex min-h-11 w-full items-center justify-between gap-3 rounded-[var(--radius-control)] border border-line bg-white px-3 py-2 text-left hover:border-blue hover:bg-pale">
              <span className="min-w-0"><span className="block truncate font-bold">{c.name}</span><span className="text-sm text-muted">{c.phone || c.email || 'No contact saved'}</span></span>
              {c.balance?.balance > 0 ? <span className="text-sm font-bold tnum text-warn">Owes {kes(c.balance.balance)}</span> : null}
            </button>
          </li>
        ))}
        {!loading && dq && !results.length ? <li className="text-muted">No customer matches “{dq}”.</li> : null}
      </ul>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => onChange({ kind: 'new', fields: { ...emptyNewCustomer, name: q } })}>Add new customer</Button>
        {allowWalkIn ? <Button variant="secondary" onClick={() => onChange({ kind: 'walkin' })}>Walk-in, pays now</Button> : null}
      </div>
    </div>
  )
}

export function ProductSearch({ products, onPick }) {
  const [q, setQ] = useState('')
  const matches = useMemo(() => {
    const t = q.trim().toLowerCase()
    if (!t) return []
    return products.filter((p) => p.name.toLowerCase().includes(t)).slice(0, 8)
  }, [q, products])
  return (
    <div className="grid gap-2">
      <Field label="Add a stock item" hint="Type part of the name. Example: A4.">
        {(p) => <Input {...p} type="search" value={q} onChange={(e) => setQ(e.target.value)} autoComplete="off" />}
      </Field>
      {matches.length ? (
        <ul className="grid gap-1">
          {matches.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                disabled={p.on_hand <= 0}
                onClick={() => { onPick(p); setQ('') }}
                className="flex min-h-11 w-full items-center justify-between gap-3 rounded-[var(--radius-control)] border border-line bg-white px-3 py-2 text-left hover:border-blue hover:bg-pale disabled:cursor-not-allowed disabled:opacity-55"
              >
                <span className="min-w-0"><span className="block truncate font-bold">{p.name}</span><span className="text-sm text-muted">{kes(p.price)} per {p.unit}{p.vat_exempt ? ', VAT exempt' : ''}</span></span>
                <span className="grid justify-items-end gap-1 text-sm tnum">{p.on_hand} left<Pill status={p.status} /></span>
              </button>
            </li>
          ))}
        </ul>
      ) : q.trim() ? <p className="m-0 text-muted">No stock item matches. Use a custom line below for services or special orders.</p> : null}
    </div>
  )
}
