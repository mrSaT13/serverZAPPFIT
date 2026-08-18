import { describe, expect, it } from 'vitest'

import { generateCodeChallenge, generateCodeVerifier } from '@/features/auth/utils/pkce'

const BASE64URL = /^[A-Za-z0-9_-]+$/

describe('generateCodeVerifier', () => {
  it('returns a base64url string with no padding', () => {
    const verifier = generateCodeVerifier()

    expect(verifier).toMatch(BASE64URL)
    expect(verifier).not.toContain('=')
    expect(verifier).not.toContain('+')
    expect(verifier).not.toContain('/')
  })

  it('encodes 32 random bytes (43-char base64url)', () => {
    expect(generateCodeVerifier()).toHaveLength(43)
  })

  it('produces a unique value on each call', () => {
    expect(generateCodeVerifier()).not.toBe(generateCodeVerifier())
  })
})

describe('generateCodeChallenge', () => {
  it('derives a deterministic base64url SHA-256 challenge from a verifier', async () => {
    const first = await generateCodeChallenge('verifier-123')
    const second = await generateCodeChallenge('verifier-123')

    expect(first).toBe(second)
    expect(first).toMatch(BASE64URL)
    expect(first).not.toContain('=')
  })

  it('matches the known RFC 7636 S256 test vector', async () => {
    // From RFC 7636 Appendix B.
    const challenge = await generateCodeChallenge('dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk')

    expect(challenge).toBe('E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM')
  })

  it('produces different challenges for different verifiers', async () => {
    const a = await generateCodeChallenge('verifier-a')
    const b = await generateCodeChallenge('verifier-b')

    expect(a).not.toBe(b)
  })
})
