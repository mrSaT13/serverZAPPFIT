import { describe, expect, it } from 'vitest'

import {
  buildPasswordRequirements,
  isValidEmail,
  isValidPassword,
  resolvePasswordMinLength,
} from '@/utils/validation'

describe('isValidEmail', () => {
  it('accepts a well-formed address and ignores surrounding whitespace', () => {
    expect(isValidEmail('user@example.com')).toBe(true)
    expect(isValidEmail('  user@example.com  ')).toBe(true)
  })

  it('rejects malformed addresses', () => {
    expect(isValidEmail('')).toBe(false)
    expect(isValidEmail('user@')).toBe(false)
    expect(isValidEmail('user@example')).toBe(false)
    expect(isValidEmail('user example.com')).toBe(false)
  })
})

describe('buildPasswordRequirements', () => {
  it('enforces character-class diversity for the strict policy', () => {
    expect(buildPasswordRequirements('strict', 10)).toEqual({
      minLength: 10,
      requireUppercase: true,
      requireLowercase: true,
      requireDigit: true,
      requireSpecialChar: true,
    })
  })

  it('enforces length only for the length_only policy', () => {
    expect(buildPasswordRequirements('length_only', 12)).toEqual({
      minLength: 12,
      requireUppercase: false,
      requireLowercase: false,
      requireDigit: false,
      requireSpecialChar: false,
    })
  })
})

describe('isValidPassword', () => {
  const strict = buildPasswordRequirements('strict', 8)
  const lengthOnly = buildPasswordRequirements('length_only', 8)

  it('accepts a password meeting every strict requirement', () => {
    expect(isValidPassword('Abcdef1!', strict)).toBe(true)
  })

  it('rejects passwords missing a required character class', () => {
    expect(isValidPassword('abcdef1!', strict)).toBe(false)
    expect(isValidPassword('ABCDEF1!', strict)).toBe(false)
    expect(isValidPassword('Abcdefg!', strict)).toBe(false)
    expect(isValidPassword('Abcdefg1', strict)).toBe(false)
  })

  it('rejects passwords shorter than the minimum length', () => {
    expect(isValidPassword('Ab1!', strict)).toBe(false)
  })

  it('accepts any sufficiently long password under the length-only policy', () => {
    expect(isValidPassword('aaaaaaaa', lengthOnly)).toBe(true)
    expect(isValidPassword('aaaaaaa', lengthOnly)).toBe(false)
  })
})

describe('resolvePasswordMinLength', () => {
  it('picks the admin length for admin accounts', () => {
    expect(resolvePasswordMinLength(8, 12, 'admin')).toBe(12)
  })

  it('picks the regular length for any other access type', () => {
    expect(resolvePasswordMinLength(8, 12, 'regular')).toBe(8)
    expect(resolvePasswordMinLength(8, 12, '')).toBe(8)
  })
})
