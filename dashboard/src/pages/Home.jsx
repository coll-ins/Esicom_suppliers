import { Link } from 'react-router-dom'
import { ButtonLink, Card, ErrorBox, Loading, PageHeader, Pill, dateText, useLoad } from '../components/ui'
import { get, post } from '../lib/api'
import { kes } from '../lib/money'

const METHOD = { mpesa: 'M-Pesa', cash: 'Cash', bank: 'Bank' }

function Stat({ label, value, sub, to }) {
  const body = (
    <>
      <div className="text-[15px] text-muted">{label}</div>
      <div className="mt-1 font-display text-[26px] font-bold tnum">{value}</div>
      {sub ? <div className="mt-1 text-sm text-muted">{sub}</div> : null}
    </>
  )
  const cls = 'block rounded-[var(--radius-card)] border border-line bg-white p-5'
  return to ? (
    <Link to={to} className={`${cls} transition-colors duration-150 hover:border-blue`}>{body}</Link>
  ) : (
    <div className={cls}>{body}</div>
  )
}

export default function Home() {
  const [data, error, reload] = useLoad(() => get('/home/'))
  const today = new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })

  return (
    <>
      <PageHeader title="Today" actions={<ButtonLink to="/sell" variant="primary">Record a sale</ButtonLink>}>{today}</PageHeader>
      <ErrorBox error={error} onRetry={reload} />
      {!data && !error ? <Loading /> : null}
      {data ? (
        <div className="grid gap-6">
          {data.alerts.length ? (
            <div className="grid gap-2">
              {data.alerts.map((a) => (
                <div key={a.id} role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-control)] border border-warn/30 bg-warn-bg px-4 py-3 text-warn">
                  <span>{a.message}</span>
                  <button type="button" className="min-h-11 rounded-md px-3 font-bold hover:bg-white/60" onClick={() => post(`/alerts/${a.id}/resolve/`).then(reload)}>
                    Mark as seen
                  </button>
                </div>
              ))}
            </div>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Stat
              label="Money collected today"
              value={kes(data.cash_collected)}
              sub={[
                ...Object.entries(data.collected_by_method).map(([m, v]) => `${METHOD[m] || m} ${kes(v)}`),
                data.refunds_today ? `less refunds ${kes(data.refunds_today)}` : '',
              ].filter(Boolean).join(', ') || 'Nothing yet today'}
              to="/payments"
            />
            <Stat label="Invoiced today" value={kes(data.invoiced)} to="/documents?type=INV" />
            <Stat label="Owed by customers" value={kes(data.owed)} sub={`${data.overdue_count} overdue ${data.overdue_count === 1 ? 'invoice' : 'invoices'}`} to="/documents?type=INV&status=overdue" />
            <Stat label="Items to reorder" value={data.reorder_count} sub="At or below reorder level" to="/buy-list" />
          </div>

          {data.new_leads ? (
            <Link to="/leads" className="flex items-center justify-between gap-3 rounded-[var(--radius-card)] border border-line bg-white p-4 hover:border-blue">
              <span><b>{data.new_leads}</b> new quote {data.new_leads === 1 ? 'request' : 'requests'} from the website</span>
              <span className="font-bold text-blue">Open leads</span>
            </Link>
          ) : null}

          <Card className="p-0">
            <div className="flex items-center justify-between px-5 pt-4">
              <h2 className="text-[18px]">Latest documents</h2>
              <Link to="/documents" className="min-h-11 content-center font-bold text-blue">See all</Link>
            </div>
            {data.recent.length ? (
              <ul className="divide-y divide-line">
                {data.recent.map((d) => (
                  <li key={d.id}>
                    <Link to={`/documents/${d.id}`} className="grid grid-cols-[1fr_auto] items-center gap-x-3 px-5 py-3 hover:bg-paper">
                      <span className="min-w-0">
                        <span className="block font-bold">{d.number}</span>
                        <span className="block truncate text-sm text-muted">{d.customer.name}, {dateText(d.issued_on)}</span>
                      </span>
                      <span className="grid justify-items-end gap-1">
                        <span className="font-bold tnum">{kes(d.total)}</span>
                        <Pill status={d.status} />
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="px-5 pb-5 text-muted">No documents yet. Record your first sale to create an invoice.</p>
            )}
          </Card>
        </div>
      ) : null}
    </>
  )
}
