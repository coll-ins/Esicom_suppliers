import { describe, expect, it } from 'vitest'
import { phoneError, stockError, wholeKes, wholeQty } from './validate'

describe('phone numbers', () => {
  it.each(['0712345678', '0712 345 678', '0112345678', '0110 123 456', '+254712345678', '254712345678', '+254 112 345 678'])(
    'accepts %s',
    (n) => expect(phoneError(n)).toBe(''),
  )
  it.each(['0812345678', '071234567', '07123456789', '+255712345678', '712345678', 'call me'])('rejects %s', (n) => {
    expect(phoneError(n)).toMatch(/07, 01 or \+254/)
  })
  it('allows an empty optional phone', () => expect(phoneError('')).toBe(''))
})

describe('stock quantity', () => {
  it('blocks selling more than is on hand, with the count', () => {
    expect(stockError('A4 paper', 21, 20)).toBe('A4 paper: only 20 left in stock. You cannot sell 21.')
  })
  it('allows selling exactly what is left', () => expect(stockError('A4 paper', 20, 20)).toBe(''))
  it('needs a whole quantity of at least 1', () => {
    expect(wholeQty('0').error).toMatch(/at least 1/)
    expect(wholeQty('2.5').error).toMatch(/whole number/)
    expect(wholeQty('3').value).toBe(3)
  })
})

describe('money input', () => {
  it('accepts commas and rejects cents', () => {
    expect(wholeKes('1,500', 'Price').value).toBe(1500)
    expect(wholeKes('20.50', 'Price').error).toMatch(/No cents/)
    expect(wholeKes('', 'Price').error).toMatch(/whole number/)
  })
})

describe('limits', () => {
  it('rejects absurd amounts before the maths breaks', () => {
    expect(wholeKes('99999999999999999999', 'Price').error).toMatch(/too large/)
    expect(wholeQty('5000000').error).toMatch(/too large/)
  })
})
