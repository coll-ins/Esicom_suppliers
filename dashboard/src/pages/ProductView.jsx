import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { MoveDialog, ProductFields, productBody, productErrors } from '../components/StockForms'
import { BackLink, Button, Card, ErrorBox, Loading, Notice, PageHeader, Pill, Table, dateText, useLoad } from '../components/ui'
import { get, patch } from '../lib/api'
import { useAuth } from '../lib/auth'
import { kes } from '../lib/money'

export default function ProductView() {
  const { id } = useParams()
  const { me } = useAuth()
  const owner = me.role === 'owner'
  const [p, error, reload] = useLoad(() => get(`/products/${id}/`), [id])
  const [f, setF] = useState(null)
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [saveError, setSaveError] = useState(null)
  const [saved, setSaved] = useState(false)
  const [move, setMove] = useState(null)

  if (error) return <><BackLink to="/stock" label="stock" /><ErrorBox error={error} onRetry={reload} /></>
  if (!p) return <Loading />
  const form = f || { ...p, price: String(p.price), reorder_level: String(p.reorder_level), cost_price: p.cost_price ?? '' }

  const save = async () => {
    const e = productErrors(form, false)
    setErrors(e)
    if (Object.keys(e).length) return
    setBusy(true)
    setSaveError(null)
    try {
      await patch(`/products/${p.id}/`, productBody(form, { owner, canVat: me.can_set_vat_exempt, isNew: false }))
      setF(null)
      setSaved(true)
      reload()
    } catch (err) {
      setSaveError(err)
    } finally {
      setBusy(false)
    }
  }

  const toggleActive = async () => {
    if (p.active && !window.confirm(`Hide ${p.name}? It disappears from sales and lists. You can restore it later.`)) return
    await patch(`/products/${p.id}/`, { active: !p.active })
    reload()
  }

  return (
    <>
      <PageHeader
        back={<BackLink to="/stock" label="stock" />}
        title={p.name}
        actions={<>
          <Button variant="secondary" onClick={() => setMove('receive')}>Receive</Button>
          <Button variant="secondary" disabled={p.on_hand <= 0} onClick={() => setMove('take_out')}>Take out</Button>
        </>}
      >
        <span className="inline-flex items-center gap-2"><b className="tnum text-navy">{p.on_hand} {p.unit}{p.on_hand === 1 ? '' : 's'} on hand</b> <Pill status={p.status} /></span>
      </PageHeader>
      {!p.active ? <Notice tone="warn">This product is hidden from sales and lists.</Notice> : null}
      <div className="mt-4 grid gap-6 lg:grid-cols-[minmax(0,1fr)_400px] lg:items-start">
        <div className="grid gap-3">
          <h2 className="text-[18px]">Stock history</h2>
          <Table head={['When', 'What', { label: 'Qty', right: true }, 'By', ...(owner ? [{ label: 'Cost', right: true }] : [])]}>
            {p.movements.map((m) => (
              <tr key={m.id}>
                <td className="whitespace-nowrap">{dateText(m.at)}</td>
                <td>{m.kind_label}{m.note ? <span className="block text-sm text-muted">{m.note}</span> : null}</td>
                <td className={`text-right font-bold tnum ${m.qty < 0 ? 'text-danger' : 'text-ok'}`}>{m.qty > 0 ? `+${m.qty}` : m.qty}</td>
                <td className="text-sm text-muted">{m.by}</td>
                {owner ? <td className="text-right tnum">{m.unit_cost !== null && m.unit_cost !== undefined ? kes(m.unit_cost) : ''}</td> : null}
              </tr>
            ))}
          </Table>
        </div>
        <Card className="grid gap-4">
          <h2 className="text-[18px]">Details</h2>
          {saved ? <Notice>Saved.</Notice> : null}
          <ErrorBox error={saveError} />
          <ProductFields f={form} setF={(v) => { setF(v); setSaved(false) }} errors={errors} />
          <Button loading={busy} onClick={save}>Save changes</Button>
          <Button variant={p.active ? 'danger' : 'secondary'} onClick={toggleActive}>{p.active ? 'Hide product' : 'Restore product'}</Button>
        </Card>
      </div>
      {move ? <MoveDialog product={p} kind={move} onClose={() => setMove(null)} onDone={() => { setMove(null); reload() }} /> : null}
    </>
  )
}
