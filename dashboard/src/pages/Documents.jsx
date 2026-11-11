import { Link, useSearchParams } from 'react-router-dom'
import { ButtonLink, Empty, ErrorBox, Field, Input, Loading, PageHeader, Pill, Select, dateText, useLoad } from '../components/ui'
import { get } from '../lib/api'
import { kes } from '../lib/money'

export default function Documents() {
  const [params, setParams] = useSearchParams()
  const f = Object.fromEntries(params)
  const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v)).toString()
  const [docs, error, reload] = useLoad(() => get(`/documents/?${qs}`), [qs])
  const set = (k) => (e) => {
    const next = { ...f, [k]: e.target.value }
    if (!next[k]) delete next[k]
    setParams(next, { replace: true })
  }

  return (
    <>
      <PageHeader title="Documents" actions={<><ButtonLink to="/quotations/new">New quotation</ButtonLink><ButtonLink to="/sell" variant="primary">Record a sale</ButtonLink></>} />
      <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Field label="Search" hint="Number or customer.">
          {(p) => <Input {...p} type="search" value={f.q || ''} onChange={set('q')} />}
        </Field>
        <Field label="Type">
          {(p) => (
            <Select {...p} value={f.type || ''} onChange={set('type')}>
              <option value="">All types</option>
              <option value="INV">Invoices</option>
              <option value="RCP">Receipts</option>
              <option value="QTN">Quotations</option>
              <option value="CN">Credit notes</option>
            </Select>
          )}
        </Field>
        <Field label="Status">
          {(p) => (
            <Select {...p} value={f.status || ''} onChange={set('status')}>
              <option value="">Any status</option>
              <option value="unpaid">Unpaid</option>
              <option value="overdue">Overdue</option>
              <option value="paid">Paid</option>
              <option value="void">Void</option>
            </Select>
          )}
        </Field>
        <Field label="From">{(p) => <Input {...p} type="date" value={f.from || ''} onChange={set('from')} />}</Field>
        <Field label="To">{(p) => <Input {...p} type="date" value={f.to || ''} onChange={set('to')} />}</Field>
      </div>
      <ErrorBox error={error} onRetry={reload} />
      {!docs && !error ? <Loading /> : null}
      {docs && !docs.length ? <Empty title="No documents match">Change the filters, or record a sale to create an invoice.</Empty> : null}
      {docs?.length ? (
        <ul className="divide-y divide-line overflow-hidden rounded-[var(--radius-card)] border border-line bg-white">
          {docs.map((d) => (
            <li key={d.id}>
              <Link to={`/documents/${d.id}`} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 px-4 py-3 hover:bg-paper sm:grid-cols-[180px_minmax(0,1fr)_120px_140px_110px]">
                <span className="font-bold">{d.number}</span>
                <span className="order-3 col-span-2 truncate text-sm text-muted sm:order-none sm:col-span-1 sm:text-base sm:text-navy">{d.customer.name}</span>
                <span className="hidden text-muted sm:block">{dateText(d.issued_on)}</span>
                <span className="text-right font-bold tnum">
                  {kes(d.total)}
                  {d.type === 'INV' && d.balance > 0 && d.balance !== d.total ? <span className="block text-sm font-normal text-muted">{kes(d.balance)} left</span> : null}
                </span>
                <span className="hidden justify-self-end sm:block"><Pill status={d.status} /></span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
      {docs?.length === 300 ? <p className="text-sm text-muted">Showing the latest 300. Use the filters to narrow down.</p> : null}
    </>
  )
}
