import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { MoveDialog, ProductFields, QuickSaleDialog, emptyProduct, productBody, productErrors } from '../components/StockForms'
import { Button, ButtonLink, Choice, Dialog, Empty, ErrorBox, Field, Input, Loading, Notice, PageHeader, Pill, useLoad } from '../components/ui'
import { get, patch, post } from '../lib/api'
import { useAuth } from '../lib/auth'
import { kes } from '../lib/money'

export default function Stock() {
  const { me } = useAuth()
  const navigate = useNavigate()
  const [list, error, reload] = useLoad(() => get('/products/'))
  const [q, setQ] = useState('')
  const [show, setShow] = useState('all')
  const [move, setMove] = useState(null)
  const [selling, setSelling] = useState(null)
  const [notice, setNotice] = useState('')
  const [adding, setAdding] = useState(false)
  const [f, setF] = useState(emptyProduct)
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [saveError, setSaveError] = useState(null)

  const rows = useMemo(() => {
    const t = q.trim().toLowerCase()
    return (list || []).filter((p) => (!t || p.name.toLowerCase().includes(t)) && (show === 'all' || p.status === show || (show === 'reorder' && p.status === 'out')))
  }, [list, q, show])

  const add = async () => {
    const e = productErrors(f, true)
    setErrors(e)
    if (Object.keys(e).length) return
    setBusy(true)
    setSaveError(null)
    try {
      const p = await post('/products/', productBody(f, { owner: me.role === 'owner', canVat: me.can_set_vat_exempt, isNew: true }))
      navigate(`/stock/${p.id}`)
    } catch (err) {
      setSaveError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader title="Stock" actions={<><ButtonLink to="/buy-list">Buy list</ButtonLink><Button onClick={() => { setF(emptyProduct); setErrors({}); setAdding(true) }}>Add product</Button></>}>
        Stock on hand is the sum of everything received, sold and taken out. It is never typed over.
      </PageHeader>
      <div className="mb-5 grid gap-3 sm:grid-cols-[minmax(0,320px)_minmax(0,420px)] sm:items-end">
        <Field label="Search">{(p) => <Input {...p} type="search" value={q} onChange={(e) => setQ(e.target.value)} />}</Field>
        <Choice label="Show" value={show} onChange={setShow} options={[{ value: 'all', label: 'All' }, { value: 'reorder', label: 'Low' }, { value: 'out', label: 'Out' }]} />
      </div>
      <ErrorBox error={error} onRetry={reload} />
      {notice ? <Notice>{notice}</Notice> : null}
      {!list && !error ? <Loading /> : null}
      {list && !list.length ? <Empty title="No products yet" action={<Button onClick={() => setAdding(true)}>Add your first product</Button>}>Add each product with the count on the shelf today.</Empty> : null}
      {list?.length && !rows.length ? <Empty title="Nothing matches">Clear the search or pick All.</Empty> : null}
      {rows.length ? (
        <ul className="divide-y divide-line overflow-hidden rounded-[var(--radius-card)] border border-line bg-white">
          {rows.map((p) => (
            <li key={p.id} className="grid gap-3 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_120px_auto] sm:items-center">
              <Link to={`/stock/${p.id}`} className="min-w-0">
                <span className="block truncate font-bold text-navy underline-offset-2 hover:underline">{p.name}</span>
                <span className="text-sm text-muted">
                  {kes(p.price)} per {p.unit}{p.vat_exempt ? ', VAT exempt' : ''}
                  {me.role === 'owner' && p.cost_price !== null && p.cost_price !== undefined ? `, cost ${kes(p.cost_price)}` : ''}
                  {p.pack_size > 1 ? `, 1 ${p.pack_label} = ${p.pack_size} ${p.unit}` : ''}
                </span>
              </Link>
              <div className="flex items-center gap-2 sm:grid sm:justify-items-end sm:gap-1">
                <b className="font-display text-[20px] tnum">{p.on_hand}</b>
                <Pill status={p.status} />
              </div>
              <div className="flex flex-wrap gap-2 sm:justify-end">
                <Button disabled={p.on_hand <= 0} onClick={() => { setNotice(''); setSelling(p) }}>Sold</Button>
                <Button variant="secondary" onClick={() => setMove({ product: p, kind: 'receive' })}>Receive</Button>
                <Button variant="secondary" disabled={p.on_hand <= 0} onClick={() => setMove({ product: p, kind: 'take_out' })}>Take out</Button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      <HiddenProducts onRestored={reload} />

      {move ? <MoveDialog product={move.product} kind={move.kind} onClose={() => setMove(null)} onDone={() => { setMove(null); reload() }} /> : null}
      {selling ? (
        <QuickSaleDialog
          product={selling}
          onClose={() => setSelling(null)}
          onDone={(r) => {
            const line = r.invoice?.lines?.[0]
            const qty = line?.qty ?? 1
            let msg = `Sold ${qty} x ${selling.name} for ${kes(r.invoice?.total ?? 0)}.`
            if (me.role === 'owner' && selling.cost_price != null && line) {
              msg += ` Profit ${kes(line.amount - selling.cost_price * qty)}.`
            }
            setSelling(null)
            setNotice(msg)
            reload()
          }}
        />
      ) : null}

      <Dialog open={adding} title="Add product" onClose={() => setAdding(false)}>
        <ErrorBox error={saveError} />
        <ProductFields f={f} setF={setF} errors={errors} isNew />
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setAdding(false)}>Cancel</Button>
          <Button loading={busy} onClick={add}>Save product</Button>
        </div>
      </Dialog>
    </>
  )
}

// Hidden products stay out of every list; restore lives here, collapsed.
function HiddenProducts({ onRestored }) {
  const [open, setOpen] = useState(false)
  const [list, error, reload] = useLoad(() => (open ? get('/products/?active=0') : Promise.resolve(null)), [open])
  return (
    <details className="mt-6 rounded-[var(--radius-card)] border border-line bg-white p-4" onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary className="min-h-11 cursor-pointer content-center font-bold">Hidden products</summary>
      <ErrorBox error={error} onRetry={reload} />
      {open && !list && !error ? <Loading /> : null}
      {list && !list.length ? <p className="text-muted">No hidden products.</p> : null}
      <ul className="mt-2 grid gap-2">
        {(list || []).map((p) => (
          <li key={p.id} className="flex items-center justify-between gap-3">
            <Link to={`/stock/${p.id}`} className="font-bold text-navy underline">{p.name}</Link>
            <Button variant="secondary" onClick={async () => { await patch(`/products/${p.id}/`, { active: true }); reload(); onRestored() }}>Restore</Button>
          </li>
        ))}
      </ul>
    </details>
  )
}
