import { useState } from 'react'
import { newKey, post } from '../lib/api'
import { useAuth } from '../lib/auth'
import { saleTotals } from '../lib/money'
import { textError, wholeKes, wholeQty } from '../lib/validate'
import { Band, Button, Check, Choice, Dialog, ErrorBox, Field, Input } from './ui'

const plural = (word) => (/[xs]$|sh$|ch$/.test(word) ? `${word}es` : `${word}s`)

// Receive (stock in) and Take out (minus) dialogs. Stock is only ever changed by movements.
export function MoveDialog({ product, kind, onClose, onDone }) {
  const { me } = useAuth()
  const owner = me.role === 'owner'
  const takeOut = kind === 'take_out'
  const hasPack = !takeOut && product?.pack_size > 1
  const [byPack, setByPack] = useState(hasPack)
  const [f, setF] = useState({ qty: '', reason: '', unit_cost: '' })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  if (!product) return null
  const label = product.pack_label || 'pack'
  const q = wholeQty(f.qty)
  const previewUnits = byPack && q.value ? q.value * product.pack_size : null

  const save = async () => {
    const e = { qty: q.error || (takeOut && q.value > product.on_hand ? `Only ${product.on_hand} left in stock.` : '') }
    if (takeOut) e.reason = textError(f.reason, 'Reason', { min: 3, max: 200 })
    if (f.unit_cost) e.unit_cost = wholeKes(f.unit_cost, 'Cost').error || ''
    const bad = Object.fromEntries(Object.entries(e).filter(([, v]) => v))
    setErrors(bad)
    if (Object.keys(bad).length) return
    setBusy(true)
    setError(null)
    try {
      const body = takeOut
        ? { qty: q.value, reason: f.reason }
        : { qty: q.value, note: f.reason, unit_cost: f.unit_cost || undefined, by_pack: byPack }
      const p = await post(`/products/${product.id}/${takeOut ? 'take-out' : 'receive'}/`, body)
      onDone(p)
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open title={`${takeOut ? 'Take out' : 'Receive'}: ${product.name}`} onClose={onClose}>
      <p className="m-0 text-muted">{product.on_hand} {product.unit}{product.on_hand === 1 ? '' : 's'} on the shelf now.</p>
      <ErrorBox error={error} />
      {hasPack ? (
        <Choice
          label="Counted as"
          value={byPack ? 'pack' : 'unit'}
          onChange={(v) => setByPack(v === 'pack')}
          options={[{ value: 'pack', label: `By the ${label}` }, { value: 'unit', label: `By the ${product.unit}` }]}
        />
      ) : null}
      <Field
        label={takeOut ? 'How many to take out' : byPack ? `How many ${plural(label)} arrived` : 'How many arrived'}
        hint={byPack ? `Each ${label} has ${product.pack_size} ${plural(product.unit)}. Example: 2.` : 'Whole number. Example: 10.'}
        error={errors.qty}
      >
        {(p) => <Input {...p} inputMode="numeric" autoFocus value={f.qty} onChange={(e) => setF({ ...f, qty: e.target.value })} />}
      </Field>
      {previewUnits ? <p className="m-0 -mt-2 text-sm text-muted">= {previewUnits} {product.unit}{previewUnits === 1 ? '' : 's'} added to stock.</p> : null}
      <Field label={takeOut ? 'Reason' : 'Note'} optional={!takeOut} hint={takeOut ? 'Example: Damaged, used in the office, counted short.' : 'Example: Delivery from Text Book Centre.'} error={errors.reason}>
        {(p) => <Input {...p} value={f.reason} maxLength={200} onChange={(e) => setF({ ...f, reason: e.target.value })} />}
      </Field>
      {!takeOut && owner ? (
        <Field label={byPack ? `Cost per ${label} (KES)` : 'Cost per item (KES)'} optional hint="What you paid, before VAT. Only the owner sees this." error={errors.unit_cost}>
          {(p) => <Input {...p} inputMode="numeric" value={f.unit_cost} onChange={(e) => setF({ ...f, unit_cost: e.target.value })} />}
        </Field>
      ) : null}
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button variant={takeOut ? 'danger' : 'primary'} loading={busy} onClick={save}>{takeOut ? 'Take out' : 'Add to stock'}</Button>
      </div>
    </Dialog>
  )
}

// One tap sale for something sold loose over the counter: pick quantity, how they paid, done.
// Creates the exact same walk-in cash sale as the full "Record a sale" screen, just with no
// customer to pick and nothing else to fill in.
export function QuickSaleDialog({ product, onClose, onDone }) {
  const { me } = useAuth()
  const [qty, setQty] = useState('1')
  const [method, setMethod] = useState('cash')
  const [reference, setReference] = useState('')
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [saveKey] = useState(newKey)
  if (!product) return null
  const q = wholeQty(qty, 'Quantity sold')
  const totals = saleTotals([{ qty: q.value || 1, unitPrice: product.price, vatExempt: product.vat_exempt }], me.vat_percent)

  const save = async () => {
    const e = {}
    if (q.error) e.qty = q.error
    else if (q.value > product.on_hand) e.qty = `Only ${product.on_hand} left in stock. You cannot sell ${q.value}.`
    if (method === 'mpesa' && !reference.trim()) e.reference = 'Enter the M-Pesa code, for example TKB7XY12AB.'
    setErrors(e)
    if (Object.keys(e).length) return
    setBusy(true)
    setError(null)
    try {
      const r = await post('/sales/', {
        walk_in: true,
        items: [{ product_id: product.id, qty: q.value }],
        paid_now: { amount: totals.total, method, reference: reference.trim() },
      }, { 'Idempotency-Key': saveKey })
      onDone(r)
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open title={`Sold: ${product.name}`} onClose={onClose}>
      <p className="m-0 text-muted">{product.on_hand} {product.unit}{product.on_hand === 1 ? '' : 's'} on the shelf.</p>
      <ErrorBox error={error} />
      <Field label="Quantity sold" hint="Whole number. Example: 1." error={errors.qty}>
        {(p) => <Input {...p} inputMode="numeric" autoFocus value={qty} onChange={(e) => setQty(e.target.value)} />}
      </Field>
      <Choice label="Paid by" value={method} onChange={setMethod} options={[{ value: 'cash', label: 'Cash' }, { value: 'mpesa', label: 'M-Pesa' }, { value: 'bank', label: 'Bank' }]} />
      {method === 'mpesa' ? (
        <Field label="M-Pesa code" hint="From the message. Example: TKB7XY12AB." error={errors.reference}>
          {(p) => <Input {...p} value={reference} maxLength={60} autoCapitalize="characters" onChange={(e) => setReference(e.target.value)} />}
        </Field>
      ) : null}
      <Band label="Total (incl. VAT)" amount={totals.total} />
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button loading={busy} onClick={save}>Record sale</Button>
      </div>
    </Dialog>
  )
}

export const emptyProduct = { name: '', unit: 'piece', price: '', cost_price: '', vat_exempt: false, reorder_level: '0', opening_qty: '0', pack_size: '1', pack_label: '' }

export function ProductFields({ f, setF, errors, isNew }) {
  const { me } = useAuth()
  const owner = me.role === 'owner'
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  return (
    <div className="grid gap-4">
      <Field label="Name" hint="As customers know it. Example: A4 printing paper, 80gsm." error={errors.name}>
        {(p) => <Input {...p} value={f.name} maxLength={160} onChange={set('name')} />}
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Sold by" hint="The unit a customer buys. Example: piece, ream." error={errors.unit}>{(p) => <Input {...p} value={f.unit} maxLength={30} onChange={set('unit')} />}</Field>
        <Field label="Selling price (KES)" hint="Per unit, before VAT. Example: 650." error={errors.price}>{(p) => <Input {...p} inputMode="numeric" value={f.price} onChange={set('price')} />}</Field>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Reorder level" hint="Goes on the buy list at or below this. Example: 5." error={errors.reorder_level}>{(p) => <Input {...p} inputMode="numeric" value={f.reorder_level} onChange={set('reorder_level')} />}</Field>
        {isNew ? <Field label="Starting stock" hint="Count on the shelf today, in units. Example: 20." error={errors.opening_qty}>{(p) => <Input {...p} inputMode="numeric" value={f.opening_qty} onChange={set('opening_qty')} />}</Field> : null}
      </div>
      <div className="grid gap-1.5 rounded-[var(--radius-control)] border border-line bg-paper p-3">
        <span className="text-[15px] font-bold">Does it arrive in packs? <span className="font-normal text-muted">(optional)</span></span>
        <span className="text-sm text-muted">Example: biscuits arrive by the box but sell one at a time. Fill this in once; "Receive" then does the counting.</span>
        <div className="mt-1 grid grid-cols-2 gap-4">
          <Field label="Pack name" hint="Example: box, carton." error={errors.pack_label}>{(p) => <Input {...p} value={f.pack_label} maxLength={30} onChange={set('pack_label')} />}</Field>
          <Field label={`${f.unit || 'Units'} per pack`} hint="Example: 24." error={errors.pack_size}>{(p) => <Input {...p} inputMode="numeric" value={f.pack_size} onChange={set('pack_size')} />}</Field>
        </div>
      </div>
      {owner ? (
        <Field label="Cost price (KES)" optional hint="What you pay per unit, before VAT. Only you see it. Used for profit." error={errors.cost_price}>
          {(p) => <Input {...p} inputMode="numeric" value={f.cost_price ?? ''} onChange={set('cost_price')} />}
        </Field>
      ) : null}
      {me.can_set_vat_exempt ? (
        <Check label="VAT exempt" hint="Tick only for items with no VAT, for example exercise books." checked={f.vat_exempt} onChange={(v) => setF({ ...f, vat_exempt: v })} />
      ) : <p className="m-0 text-sm text-muted">VAT: {f.vat_exempt ? 'exempt' : 'charged'}. Only the owner can change this.</p>}
    </div>
  )
}

export function productErrors(f, isNew) {
  const packSize = wholeQty(f.pack_size || '1', 'Units per pack', { min: 1 })
  const packLabel = (f.pack_label || '').trim()
  const e = {
    name: textError(f.name, 'Name', { min: 2, max: 160 }),
    unit: textError(f.unit, 'Unit', { min: 1, max: 30 }),
    price: wholeKes(f.price, 'Selling price').error || '',
    reorder_level: wholeQty(f.reorder_level, 'Reorder level', { min: 0 }).error || '',
    opening_qty: isNew ? wholeQty(f.opening_qty, 'Starting stock', { min: 0 }).error || '' : '',
    cost_price: f.cost_price !== '' && f.cost_price !== null && f.cost_price !== undefined ? wholeKes(f.cost_price, 'Cost price').error || '' : '',
    pack_size: packSize.error || (packLabel && packSize.value < 2 ? 'Must be at least 2, or leave the pack name empty.' : ''),
    pack_label: !packLabel && packSize.value > 1 ? 'Name the pack, for example box.' : '',
  }
  return Object.fromEntries(Object.entries(e).filter(([, v]) => v))
}

export function productBody(f, { owner, canVat, isNew }) {
  const packLabel = (f.pack_label || '').trim()
  const body = {
    name: f.name.trim(), unit: f.unit.trim(), price: f.price, reorder_level: f.reorder_level,
    pack_size: packLabel ? f.pack_size : '1', pack_label: packLabel,
  }
  if (isNew) body.opening_qty = f.opening_qty
  if (owner) body.cost_price = f.cost_price === '' ? null : f.cost_price
  if (canVat) body.vat_exempt = f.vat_exempt
  return body
}
