// Same rules as backend/ledger/money.py: whole shillings, VAT per line rounded half up.

const fmt = new Intl.NumberFormat('en-KE', { maximumFractionDigits: 0 })

export function kes(amount) {
  return `KES ${fmt.format(amount || 0)}`
}

export function num(amount) {
  return fmt.format(amount || 0)
}

export function lineAmount(qty, unitPrice) {
  return qty * unitPrice
}

// Integer maths so 0.5 always rounds up and floating point never drifts.
export function lineVat(amount, vatExempt, percent = 16) {
  if (vatExempt) return 0
  return Math.floor((amount * percent + 50) / 100)
}

export function saleTotals(lines, percent = 16) {
  let subtotal = 0
  let vat = 0
  for (const line of lines) {
    const amount = lineAmount(line.qty, line.unitPrice)
    subtotal += amount
    vat += lineVat(amount, line.vatExempt, percent)
  }
  return {
    subtotal,
    vat,
    total: subtotal + vat,
    showVat: lines.some((l) => !l.vatExempt),
  }
}
