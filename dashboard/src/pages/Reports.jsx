import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Band, Card, Choice, Empty, ErrorBox, Field, Input, Loading, PageHeader, Table, TotalsRows, todayIso, useLoad } from '../components/ui'
import { get } from '../lib/api'
import { useAuth } from '../lib/auth'
import { kes, num } from '../lib/money'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const METHOD = { mpesa: 'M-Pesa', cash: 'Cash', bank: 'Bank' }

function Money({ range }) {
  const [d, error, reload] = useLoad(() => get(`/reports/money/?from=${range.from}&to=${range.to}`), [range.from, range.to])
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (!d) return <Loading />
  const max = Math.max(1, ...d.by_day.map((r) => r.in))
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start">
      <Card className="grid gap-3">
        <h2 className="text-[18px]">Money in by day</h2>
        {d.by_day.length ? (
          <ul className="grid gap-1.5">
            {d.by_day.map((r) => (
              <li key={r.day} className="grid grid-cols-[88px_minmax(0,1fr)_110px] items-center gap-3 text-[15px]">
                <span className="text-muted">{new Date(r.day + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}</span>
                <span className="h-3 rounded-full bg-pale"><span className="block h-3 origin-left rounded-full bg-blue" style={{ transform: `scaleX(${r.in / max})` }} /></span>
                <span className="text-right font-bold tnum">{kes(r.in)}</span>
              </li>
            ))}
          </ul>
        ) : <p className="m-0 text-muted">No money received in these dates.</p>}
      </Card>
      <Card className="grid gap-3">
        <TotalsRows rows={[
          ...Object.entries(d.by_method).map(([m, v]) => [METHOD[m] || m, v]),
          ['Refunds paid out', d.refunds_out],
          d.stock_bought !== undefined && ['Stock bought (cost)', d.stock_bought],
        ]} />
        <Band label="Money in, after refunds" amount={d.money_in - d.refunds_out} />
      </Card>
    </div>
  )
}

function Aging() {
  const [d, error, reload] = useLoad(() => get('/reports/aging/'))
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (!d) return <Loading />
  const cols = ['0-30', '31-60', '61-90', '90+']
  return (
    <div className="grid gap-4">
      <p className="m-0 text-muted">Unpaid invoices by days since they were issued.</p>
      <div className="grid gap-3 sm:grid-cols-4">
        {cols.map((c) => (
          <Card key={c} className="p-4"><div className="text-muted">{c} days</div><div className={`font-display text-[22px] font-bold tnum ${c === '90+' && d.buckets[c] ? 'text-danger' : ''}`}>{kes(d.buckets[c])}</div></Card>
        ))}
      </div>
      {d.customers.length ? (
        <Table head={['Customer', ...cols.map((c) => ({ label: c, right: true })), { label: 'Total', right: true }]}>
          {d.customers.map((r) => (
            <tr key={r.id}>
              <td><Link to={`/customers/${r.id}`} className="font-bold text-navy underline">{r.customer}</Link></td>
              {cols.map((c) => <td key={c} className="text-right tnum">{r[c] ? num(r[c]) : ''}</td>)}
              <td className="text-right font-bold tnum">{num(r.total)}</td>
            </tr>
          ))}
        </Table>
      ) : <Empty title="Nobody owes anything" />}
    </div>
  )
}

function Sales({ range }) {
  const [d, error, reload] = useLoad(() => get(`/reports/sales/?from=${range.from}&to=${range.to}`), [range.from, range.to])
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (!d) return <Loading />
  return (
    <div className="grid gap-6">
      <Band label="Invoiced in these dates (incl. VAT)" amount={d.total} />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="grid gap-2">
          <h2 className="text-[18px]">By customer</h2>
          <Table head={['Customer', { label: 'Invoices', right: true }, { label: 'Total', right: true }]}>
            {d.by_customer.map((r) => (
              <tr key={r.id}><td><Link to={`/customers/${r.id}`} className="text-navy underline">{r.name}</Link></td><td className="text-right tnum">{r.count}</td><td className="text-right font-bold tnum">{num(r.total)}</td></tr>
            ))}
          </Table>
        </div>
        <div className="grid gap-2">
          <h2 className="text-[18px]">By product (before VAT)</h2>
          <Table head={['Product', { label: 'Qty', right: true }, { label: 'Sales', right: true }]}>
            {d.by_product.map((r) => (
              <tr key={r.name}><td>{r.name}</td><td className="text-right tnum">{num(r.qty)}</td><td className="text-right font-bold tnum">{num(r.sales)}</td></tr>
            ))}
          </Table>
        </div>
      </div>
    </div>
  )
}

function Profit({ range }) {
  const [d, error, reload] = useLoad(() => get(`/reports/profit/?from=${range.from}&to=${range.to}`), [range.from, range.to])
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (!d) return <Loading />
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start">
      <Table head={['Item', { label: 'Sales', right: true }, { label: 'Cost', right: true }, { label: 'Profit', right: true }]}>
        {d.items.map((r) => (
          <tr key={r.name}>
            <td>{r.name}{r.cost_unknown ? <span className="block text-sm text-muted">{kes(r.cost_unknown)} sold with no cost price</span> : null}</td>
            <td className="text-right tnum">{num(r.sales)}</td>
            <td className="text-right tnum">{num(r.cost)}</td>
            <td className={`text-right font-bold tnum ${r.profit < 0 ? 'text-danger' : ''}`}>{num(r.profit)}</td>
          </tr>
        ))}
      </Table>
      <Card className="grid gap-3">
        <TotalsRows rows={[['Sales before VAT', d.sales_ex_vat], ['Cost of those items', d.cost], d.sales_without_cost > 0 && ['Sales with no cost price', d.sales_without_cost]]} />
        <Band label="Profit" amount={d.profit} />
        <p className="m-0 text-sm text-muted">{d.note}</p>
      </Card>
    </div>
  )
}

function Vat() {
  const [year, setYear] = useState(new Date().getFullYear())
  const [d, error, reload] = useLoad(() => get(`/reports/vat/?year=${year}`), [year])
  return (
    <div className="grid gap-4">
      <div className="max-w-40"><Field label="Year">{(p) => <Input {...p} inputMode="numeric" value={year} onChange={(e) => /^\d{0,4}$/.test(e.target.value) && setYear(e.target.value)} />}</Field></div>
      <ErrorBox error={error} onRetry={reload} />
      {d ? (
        <>
          <Table head={['Month', { label: 'Taxable sales', right: true }, { label: 'Exempt sales', right: true }, { label: 'VAT charged', right: true }]}>
            {d.months.map((m) => (
              <tr key={m.month}><td>{MONTHS[m.month - 1]}</td><td className="text-right tnum">{num(m.taxable)}</td><td className="text-right tnum">{num(m.exempt)}</td><td className="text-right font-bold tnum">{num(m.vat)}</td></tr>
            ))}
          </Table>
          <p className="m-0 text-sm text-muted">{d.note} Amounts before VAT. Use this when filing; eTIMS invoices are still issued on the KRA portal.</p>
        </>
      ) : !error ? <Loading /> : null}
    </div>
  )
}

export default function Reports() {
  const { me } = useAuth()
  const [tab, setTab] = useState('money')
  const [range, setRange] = useState({ from: todayIso().slice(0, 8) + '01', to: todayIso() })
  const tabs = [
    { value: 'money', label: 'Money' }, { value: 'aging', label: 'Owed' }, { value: 'sales', label: 'Sales' },
    ...(me.role === 'owner' ? [{ value: 'profit', label: 'Profit' }] : []), { value: 'vat', label: 'VAT' },
  ]
  return (
    <>
      <PageHeader title="Reports" />
      <div className="mb-5 grid gap-4">
        <div className="overflow-x-auto"><div className="min-w-[420px] max-w-2xl"><Choice label="Report" value={tab} onChange={setTab} options={tabs} /></div></div>
        {['money', 'sales', 'profit'].includes(tab) ? (
          <div className="grid max-w-lg grid-cols-2 gap-4">
            <Field label="From">{(p) => <Input {...p} type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} />}</Field>
            <Field label="To">{(p) => <Input {...p} type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} />}</Field>
          </div>
        ) : null}
      </div>
      {tab === 'money' ? <Money range={range} /> : null}
      {tab === 'aging' ? <Aging /> : null}
      {tab === 'sales' ? <Sales range={range} /> : null}
      {tab === 'profit' ? <Profit range={range} /> : null}
      {tab === 'vat' ? <Vat /> : null}
    </>
  )
}
