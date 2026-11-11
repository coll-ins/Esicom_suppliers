import { useState } from 'react'
import { post } from '../lib/api'
import { useAuth } from '../lib/auth'
import { textError, wholeKes, wholeQty } from '../lib/validate'
import { Button, Check, Dialog, ErrorBox, Field, Input } from './ui'

// Receive (stock in) and Take out (minus) dialogs. Stock is only ever changed by movements.
export function MoveDialog({ product, kind, onClose, onDone }) {
  const { me } = useAuth()
  const owner = me.role === 'owner'
  const [f, setF] = useState({ qty: '', reason: '', unit_cost: '' })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  if (!product) return null
  const takeOut = kind === 'take_out'

  const save = async () => {
    const q = wholeQty(f.qty)
    const e = { qty: q.error || (takeOut && q.value > product.on_hand ? `Only ${product.on_hand} left in stock.` : '') }
    if (takeOut) e.reason = textError(f.reason, 'Reason', { min: 3, max: 200 })
    if (f.unit_cost) e.unit_cost = wholeKes(f.unit_cost, 'Cost per item').error || ''
    const bad = Object.fromEntries(Object.entries(e).filter(([, v]) => v))
    setErrors(bad)
    if (Object.keys(bad).length) return
    setBusy(true)
    setError(null)
    try {
      const body = takeOut ? { qty: q.value, reason: f.reason } : { qty: q.value, note: f.reason, unit_cost: f.unit_cost || undefined }
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
      <Field label={takeOut ? 'How many to take out' : 'How many arrived'} hint="Whole number. Example: 10." error={errors.qty}>
        {(p) => <Input {...p} inputMode="numeric" autoFocus value={f.qty} onChange={(e) => setF({ ...f, qty: e.target.value })} />}
      </Field>
      <Field label={takeOut ? 'Reason' : 'Note'} optional={!takeOut} hint={takeOut ? 'Example: Damaged, used in the office, counted short.' : 'Example: Delivery from Text Book Centre.'} error={errors.reason}>
        {(p) => <Input {...p} value={f.reason} maxLength={200} onChange={(e) => setF({ ...f, reason: e.target.value })} />}
      </Field>
      {!takeOut && owner ? (
        <Field label="Cost per item (KES)" optional hint="What you paid, before VAT. Only the owner sees this." error={errors.unit_cost}>
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

export const emptyProduct = { name: '', unit: 'piece', price: '', cost_price: '', vat_exempt: false, reorder_level: '0', opening_qty: '0' }

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
        <Field label="Unit" hint="Example: ream, box, piece." error={errors.unit}>{(p) => <Input {...p} value={f.unit} maxLength={30} onChange={set('unit')} />}</Field>
        <Field label="Selling price (KES)" hint="Before VAT. Example: 650." error={errors.price}>{(p) => <Input {...p} inputMode="numeric" value={f.price} onChange={set('price')} />}</Field>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Reorder level" hint="Goes on the buy list at or below this. Example: 5." error={errors.reorder_level}>{(p) => <Input {...p} inputMode="numeric" value={f.reorder_level} onChange={set('reorder_level')} />}</Field>
        {isNew ? <Field label="Starting stock" hint="Count on the shelf today. Example: 20." error={errors.opening_qty}>{(p) => <Input {...p} inputMode="numeric" value={f.opening_qty} onChange={set('opening_qty')} />}</Field> : null}
      </div>
      {owner ? (
        <Field label="Cost price (KES)" optional hint="What you pay, before VAT. Only you see it. Used for profit." error={errors.cost_price}>
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
  const e = {
    name: textError(f.name, 'Name', { min: 2, max: 160 }),
    unit: textError(f.unit, 'Unit', { min: 1, max: 30 }),
    price: wholeKes(f.price, 'Selling price').error || '',
    reorder_level: wholeQty(f.reorder_level, 'Reorder level', { min: 0 }).error || '',
    opening_qty: isNew ? wholeQty(f.opening_qty, 'Starting stock', { min: 0 }).error || '' : '',
    cost_price: f.cost_price !== '' && f.cost_price !== null && f.cost_price !== undefined ? wholeKes(f.cost_price, 'Cost price').error || '' : '',
  }
  return Object.fromEntries(Object.entries(e).filter(([, v]) => v))
}

export function productBody(f, { owner, canVat, isNew }) {
  const body = { name: f.name.trim(), unit: f.unit.trim(), price: f.price, reorder_level: f.reorder_level }
  if (isNew) body.opening_qty = f.opening_qty
  if (owner) body.cost_price = f.cost_price === '' ? null : f.cost_price
  if (canVat) body.vat_exempt = f.vat_exempt
  return body
}
