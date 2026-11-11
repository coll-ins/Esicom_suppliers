import { useState } from 'react'
import { ButtonLink, Choice, Empty, ErrorBox, Loading, PageHeader, Pill, Select, dateText, useLoad } from '../components/ui'
import { get, patch } from '../lib/api'

export default function Leads() {
  const [status, setStatus] = useState('open')
  const [list, error, reload, setList] = useLoad(() => get('/leads/'))
  const [saveError, setSaveError] = useState(null)
  const rows = (list || []).filter((l) => status === 'all' || (status === 'open' ? l.status !== 'closed' : l.status === status))

  const change = async (lead, value) => {
    setSaveError(null)
    try {
      const updated = await patch(`/leads/${lead.id}/`, { status: value })
      setList(list.map((l) => (l.id === lead.id ? updated : l)))
    } catch (e) {
      setSaveError(e)
    }
  }

  return (
    <>
      <PageHeader title="Website leads">Quote requests from the website form. Prices are never shown on the website, so reply with a quotation.</PageHeader>
      <div className="mb-5 max-w-md"><Choice label="Show" value={status} onChange={setStatus} options={[{ value: 'open', label: 'Open' }, { value: 'new', label: 'New' }, { value: 'all', label: 'All' }]} /></div>
      <ErrorBox error={error || saveError} onRetry={error ? reload : undefined} />
      {!list && !error ? <Loading /> : null}
      {list && !rows.length ? <Empty title="No leads here">New requests from the website's Request a quote form appear here.</Empty> : null}
      <ul className="grid gap-3">
        {rows.map((l) => (
          <li key={l.id} className="grid gap-3 rounded-[var(--radius-card)] border border-line bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <div className="font-bold">{l.name}{l.company ? `, ${l.company}` : ''}</div>
                <div className="text-sm text-muted">
                  {dateText(l.created_at)}. <a className="text-blue underline" href={`tel:${l.phone}`}>{l.phone}</a>
                  {l.email ? <>. <a className="text-blue underline" href={`mailto:${l.email}`}>{l.email}</a></> : null}
                </div>
              </div>
              <Pill status={l.status} />
            </div>
            <p className="m-0 max-w-[75ch] whitespace-pre-line">{l.needs}</p>
            {l.quantity || l.required_date ? <p className="m-0 text-sm text-muted">{[l.quantity && `Quantity: ${l.quantity}`, l.required_date && `Needed by ${dateText(l.required_date)}`].filter(Boolean).join('. ')}</p> : null}
            <div className="flex flex-wrap items-end gap-2">
              <ButtonLink to={`/quotations/new?lead=${l.id}`} variant="primary">Create quotation</ButtonLink>
              <label className="grid gap-1 text-sm font-bold">
                Status
                <Select value={l.status} onChange={(e) => change(l, e.target.value)}>
                  <option value="new">New</option>
                  <option value="contacted">Contacted</option>
                  <option value="quoted">Quoted</option>
                  <option value="closed">Closed</option>
                </Select>
              </label>
            </div>
          </li>
        ))}
      </ul>
    </>
  )
}
