import { describe, expect, it } from 'vitest'

import { cmToFeetInches, feetAndInchesToCm, kmToMiles, milesToKm } from '@/utils/units'

describe('cmToFeetInches', () => {
  it('converts centimetres to whole feet and rounded inches', () => {
    expect(cmToFeetInches(180)).toEqual({ feet: 5, inches: 11 })
    expect(cmToFeetInches(0)).toEqual({ feet: 0, inches: 0 })
  })

  it('carries over to the next foot instead of returning 12 inches', () => {
    expect(cmToFeetInches(182)).toEqual({ feet: 6, inches: 0 })
  })
})

describe('feetAndInchesToCm', () => {
  it('converts feet and inches to whole centimetres', () => {
    expect(feetAndInchesToCm(5, 11)).toBe(180)
    expect(feetAndInchesToCm(0, 0)).toBe(0)
  })

  it('round-trips approximately with cmToFeetInches', () => {
    const { feet, inches } = cmToFeetInches(175)
    expect(feetAndInchesToCm(feet, inches)).toBeCloseTo(175, -1)
  })
})

describe('kmToMiles / milesToKm', () => {
  it('converts kilometres to miles', () => {
    expect(kmToMiles(1.609344)).toBeCloseTo(1, 6)
    expect(kmToMiles(0)).toBe(0)
  })

  it('converts miles to kilometres', () => {
    expect(milesToKm(1)).toBeCloseTo(1.609344, 6)
    expect(milesToKm(0)).toBe(0)
  })

  it('round-trips kilometres through miles', () => {
    expect(milesToKm(kmToMiles(42.195))).toBeCloseTo(42.195, 6)
  })
})
