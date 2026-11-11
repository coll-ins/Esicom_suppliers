import { describe, expect, it } from 'vitest'
import { kes, lineVat, saleTotals } from './money'

describe('sale totals', () => {
  it('rounds VAT per line to the whole shilling, like the backend', () => {
    expect(lineVat(17998, false)).toBe(2880) // 2879.68
    expect(lineVat(103, false)).toBe(16) // 16.48
    expect(lineVat(97, false)).toBe(16) // 15.52
    expect(lineVat(3, false)).toBe(0) // 0.48
    expect(lineVat(10000, true)).toBe(0)
  })

  it('adds lines, VAT and exempt items', () => {
    const t = saleTotals([
      { qty: 10, unitPrice: 650 },
      { qty: 20, unitPrice: 1150 },
      { qty: 2, unitPrice: 8999 },
      { qty: 50, unitPrice: 45, vatExempt: true },
    ])
    expect(t).toEqual({ subtotal: 49748, vat: 7600, total: 57348, showVat: true })
  })

  it('rounds per line, not on the total', () => {
    const t = saleTotals([{ qty: 1, unitPrice: 3 }, { qty: 1, unitPrice: 3 }, { qty: 1, unitPrice: 3 }])
    expect(t.vat).toBe(0)
    expect(t.total).toBe(9)
  })

  it('hides the VAT row when every line is exempt', () => {
    expect(saleTotals([{ qty: 50, unitPrice: 45, vatExempt: true }]).showVat).toBe(false)
  })

  it('uses the configured VAT rate', () => {
    expect(saleTotals([{ qty: 1, unitPrice: 1000 }], 8).total).toBe(1080)
  })

  it('formats whole shillings with commas', () => {
    expect(kes(57348)).toBe('KES 57,348')
  })
})
