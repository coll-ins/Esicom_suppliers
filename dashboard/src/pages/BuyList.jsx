import { Link } from 'react-router-dom'
import { Button, Empty, ErrorBox, Loading, PageHeader, Table, useLoad } from '../components/ui'
import { get } from '../lib/api'

export default function BuyList() {
  const [rows, error, reload] = useLoad(() => get('/buy-list/'))
  return (
    <>
      <PageHeader title="Buy list" actions={<Button variant="secondary" onClick={() => window.print()}>Print</Button>}>
        Products at or below their reorder level. Order enough to reach: reorder level + average monthly sales over the last 3 months.
      </PageHeader>
      <ErrorBox error={error} onRetry={reload} />
      {!rows && !error ? <Loading /> : null}
      {rows && !rows.length ? <Empty title="Nothing to buy">Every product is above its reorder level.</Empty> : null}
      {rows?.length ? (
        <div className="print-area">
          <Table head={['Product', { label: 'On hand', right: true }, { label: 'Reorder at', right: true }, { label: 'Sold, 3 months', right: true }, { label: 'Order', right: true }]}>
            {rows.map((r) => (
              <tr key={r.id}>
                <td><Link to={`/stock/${r.id}`} className="font-bold text-navy underline">{r.name}</Link><span className="block text-sm text-muted">{r.basis}</span></td>
                <td className="text-right tnum">{r.on_hand}</td>
                <td className="text-right tnum">{r.reorder_level}</td>
                <td className="text-right tnum">{r.sold_last_3_months}</td>
                <td className="text-right font-display text-[18px] font-bold tnum">{r.order_qty} {r.unit}{r.order_qty === 1 ? '' : 's'}</td>
              </tr>
            ))}
          </Table>
        </div>
      ) : null}
    </>
  )
}
