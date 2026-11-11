import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CustomerPicker, emptyNewCustomer, newCustomerErrors } from '../components/pickers'
import { Button, Dialog, Empty, ErrorBox, Field, Input, Loading, PageHeader, useLoad } from '../components/ui'
import { get, post } from '../lib/api'
import { kes } from '../lib/money'

export default function Customers() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [list, error, reload] = useLoad(() => get(`/customers/?q=${encodeURIComponent(q)}`), [q])
  const [adding, setAdding] = useState(null)
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [saveError, setSaveError] = useState(null)

  const save = async () => {
    const e = Object.fromEntries(Object.entries(newCustomerErrors(adding.fields)).filter(([, v]) => v))
    setErrors(e)
    if (Object.keys(e).length) return
    setBusy(true)
    setSaveError(null)
    try {
      const c = await post('/customers/', adding.fields)
      navigate(`/customers/${c.id}`)
    } catch (err) {
      setSaveError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader title="Customers" actions={<Button onClick={() => { setAdding({ kind: 'new', fields: emptyNewCustomer }); setErrors({}) }}>Add customer</Button>} />
      <div className="mb-5 max-w-md">
        <Field label="Search" hint="Name, phone or email.">
          {(p) => <Input {...p} type="search" value={q} onChange={(e) => setQ(e.target.value)} />}
        </Field>
      </div>
      <ErrorBox error={error} onRetry={reload} />
      {!list && !error ? <Loading /> : null}
      {list && !list.length ? <Empty title={q ? `No customer matches “${q}”` : 'No customers yet'}>Add a customer, or record a sale and add them there.</Empty> : null}
      {list?.length ? (
        <ul className="divide-y divide-line overflow-hidden rounded-[var(--radius-card)] border border-line bg-white">
          {list.map((c) => (
            <li key={c.id}>
              <Link to={`/customers/${c.id}`} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-4 py-3 hover:bg-paper">
                <span className="min-w-0">
                  <span className="block truncate font-bold">{c.name}</span>
                  <span className="block truncate text-sm text-muted">{[c.phone, c.billing === 'tab' ? 'Running tab' : null].filter(Boolean).join(', ') || 'No phone saved'}</span>
                </span>
                <span className="text-right tnum">
                  {c.balance.balance > 0 ? <b>{kes(c.balance.balance)}</b> : c.balance.credit > 0 ? <span className="text-ok">Credit {kes(c.balance.credit)}</span> : <span className="text-muted">Nothing owed</span>}
                  {c.credit_limit !== null && c.balance.balance > c.credit_limit ? <span className="block text-sm font-bold text-danger">Over limit</span> : null}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}

      <Dialog open={!!adding} title="Add customer" onClose={() => setAdding(null)}>
        <ErrorBox error={saveError} />
        {adding ? <CustomerPicker value={adding} onChange={(v) => setAdding(v || { kind: 'new', fields: emptyNewCustomer })} allowWalkIn={false} errors={errors} /> : null}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setAdding(null)}>Cancel</Button>
          <Button loading={busy} onClick={save}>Save customer</Button>
        </div>
      </Dialog>
    </>
  )
}
