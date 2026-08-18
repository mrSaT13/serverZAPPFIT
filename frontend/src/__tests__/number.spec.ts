import { describe, expect, it } from 'vitest'

import { toNumberOrNull } from '@/utils/number'

describe('toNumberOrNull', () => {
  it('returns a finite number unchanged', () => {
    expect(toNumberOrNull(42)).toBe(42)
    expect(toNumberOrNull(0)).toBe(0)
    expect(toNumberOrNull(-3.5)).toBe(-3.5)
  })

  it('returns null for non-finite numbers', () => {
    expect(toNumberOrNull(Number.NaN)).toBeNull()
    expect(toNumberOrNull(Number.POSITIVE_INFINITY)).toBeNull()
    expect(toNumberOrNull(Number.NEGATIVE_INFINITY)).toBeNull()
  })

  it('parses numeric strings, trimming surrounding whitespace', () => {
    expect(toNumberOrNull('42')).toBe(42)
    expect(toNumberOrNull(' 3.5 ')).toBe(3.5)
    expect(toNumberOrNull('-7')).toBe(-7)
  })

  it('treats blank strings as null', () => {
    expect(toNumberOrNull('')).toBeNull()
    expect(toNumberOrNull('   ')).toBeNull()
  })

  it('returns null for unparseable strings', () => {
    expect(toNumberOrNull('abc')).toBeNull()
    expect(toNumberOrNull('1,234')).toBeNull()
    expect(toNumberOrNull('12px')).toBeNull()
  })
})
