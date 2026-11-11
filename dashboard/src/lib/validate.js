// Same checks as backend/ledger/validators.py. Each returns '' when fine, or a plain reason.

export const PHONE_HELP = 'Kenyan number starting 07, 01 or +254, for example 0712 345 678.'

export function phoneError(raw) {
  const digits = String(raw || '').replace(/[\s\-().]/g, '')
  if (!digits) return ''
  return /^(?:\+254|254|0)[17]\d{8}$/.test(digits) ? '' : `Not a callable Kenyan number. Use ${PHONE_HELP}`
}

export function wholeKes(raw, field, { min = 0 } = {}) {
  const text = String(raw ?? '').replace(/,/g, '').trim()
  if (!/^\d+$/.test(text)) return { error: `${field} must be a whole number of shillings, for example 1500. No cents.` }
  const value = Number(text)
  if (value < min) return { error: `${field} must be at least ${min.toLocaleString('en-KE')}.` }
  return { value }
}

export function wholeQty(raw, field = 'Quantity', { min = 1 } = {}) {
  const text = String(raw ?? '').replace(/,/g, '').trim()
  if (!/^\d+$/.test(text)) return { error: `${field} must be a whole number, for example 5.` }
  const value = Number(text)
  if (value < min) return { error: `${field} must be at least ${min}.` }
  return { value }
}

// Quantity asked for a stock item across the whole sale, against what is on the shelf.
export function stockError(name, wanted, onHand) {
  if (wanted > onHand) return `${name}: only ${onHand} left in stock. You cannot sell ${wanted}.`
  return ''
}

export function textError(raw, field, { min = 0, max }) {
  const value = String(raw || '').trim()
  if (value.length < min) return min <= 1 ? `${field} is required.` : `${field} must be at least ${min} characters.`
  if (value.length > max) return `${field} must be ${max} characters or fewer.`
  if (value && !/[A-Za-z0-9]/.test(value)) return `${field} must contain letters or numbers.`
  return ''
}

export function emailError(raw) {
  const value = String(raw || '').trim()
  if (!value) return ''
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) ? '' : 'Email must look like name@example.com.'
}
