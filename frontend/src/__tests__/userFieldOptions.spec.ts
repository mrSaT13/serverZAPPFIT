import { describe, expect, it } from 'vitest'

import {
  CURRENCY_OPTIONS,
  GENDER_OPTIONS,
  LANGUAGE_CODES,
  numberRange,
  resolveHeightCm,
  WEEKDAY_OPTIONS,
} from '@/features/users/utils/userFieldOptions'

describe('numberRange', () => {
  const validate = numberRange(10, 'out of range')

  it('passes a null (empty) value', () => {
    expect(validate(null)).toBeNull()
  })

  it('passes values within the inclusive 0..max range', () => {
    expect(validate(0)).toBeNull()
    expect(validate(5)).toBeNull()
    expect(validate(10)).toBeNull()
  })

  it('rejects values above the maximum', () => {
    expect(validate(11)).toBe('out of range')
  })

  it('rejects negative values', () => {
    expect(validate(-1)).toBe('out of range')
  })
})

describe('resolveHeightCm', () => {
  it('returns the centimetre value as-is in metric', () => {
    expect(
      resolveHeightCm({ units: 'metric', heightCm: 180, heightFeet: null, heightInches: null }),
    ).toBe(180)
  })

  it('returns null in metric when no centimetre value is set', () => {
    expect(
      resolveHeightCm({ units: 'metric', heightCm: null, heightFeet: null, heightInches: null }),
    ).toBeNull()
  })

  it('returns null in imperial when both feet and inches are unset', () => {
    expect(
      resolveHeightCm({ units: 'imperial', heightCm: null, heightFeet: null, heightInches: null }),
    ).toBeNull()
  })

  it('converts feet and inches to centimetres in imperial', () => {
    expect(
      resolveHeightCm({ units: 'imperial', heightCm: null, heightFeet: 5, heightInches: 11 }),
    ).toBe(180)
  })

  it('treats a missing inches component as zero', () => {
    expect(
      resolveHeightCm({ units: 'imperial', heightCm: null, heightFeet: 6, heightInches: null }),
    ).toBe(183)
  })
})

describe('account field option lists', () => {
  it('expose non-empty, unique option values', () => {
    for (const options of [LANGUAGE_CODES, GENDER_OPTIONS, WEEKDAY_OPTIONS, CURRENCY_OPTIONS]) {
      expect(options.length).toBeGreaterThan(0)
      expect(new Set(options).size).toBe(options.length)
    }
  })
})
