import { describe, expect, it, vi } from 'vitest'

import {
  fetchBackendVersion,
  fetchLatestPreRelease,
  fetchLatestRelease,
  isNewerVersion,
  isPreRelease,
} from '@/features/core/services/updateCheck'

vi.mock('@/services/http', () => ({
  apiFetch: vi.fn<typeof import('@/services/http').apiFetch>(),
}))

describe('isNewerVersion', () => {
  it('returns true when latest is greater (patch)', () => {
    expect(isNewerVersion('0.20.0', '0.20.1')).toBe(true)
  })

  it('returns true when latest is greater (minor)', () => {
    expect(isNewerVersion('0.20.5', '0.21.0')).toBe(true)
  })

  it('returns true when latest is greater (major)', () => {
    expect(isNewerVersion('1.0.0', '2.0.0')).toBe(true)
  })

  it('returns false when versions are equal', () => {
    expect(isNewerVersion('0.20.0', '0.20.0')).toBe(false)
  })

  it('returns false when current is greater', () => {
    expect(isNewerVersion('0.21.0', '0.20.5')).toBe(false)
  })

  it('handles missing patch segment', () => {
    expect(isNewerVersion('0.20', '0.21')).toBe(true)
  })

  it('returns true when latest is a later beta of the same version', () => {
    expect(isNewerVersion('0.19.0-beta1', '0.19.0-beta2')).toBe(true)
  })

  it('returns false when latest is an earlier beta of the same version', () => {
    expect(isNewerVersion('0.19.0-beta2', '0.19.0-beta1')).toBe(false)
  })

  it('returns false when pre-release versions are equal', () => {
    expect(isNewerVersion('0.19.0-beta1', '0.19.0-beta1')).toBe(false)
  })

  it('returns true when latest is stable and current is a pre-release', () => {
    expect(isNewerVersion('0.19.0-beta2', '0.19.0')).toBe(true)
  })

  it('returns false when current is stable and latest is a pre-release', () => {
    expect(isNewerVersion('0.19.0', '0.19.0-beta2')).toBe(false)
  })
})

describe('fetchBackendVersion', () => {
  it('fetches /about and returns the version string, stripping leading v', async () => {
    const { apiFetch } = await import('@/services/http')
    vi.mocked(apiFetch).mockResolvedValueOnce({ name: 'Endurain API', version: 'v0.20.0' })

    const version = await fetchBackendVersion()
    expect(apiFetch).toHaveBeenCalledWith('/about', expect.objectContaining({ auth: false }))
    expect(version).toBe('0.20.0')
  })

  it('returns the version unchanged when there is no leading v', async () => {
    const { apiFetch } = await import('@/services/http')
    vi.mocked(apiFetch).mockResolvedValueOnce({ name: 'Endurain API', version: '0.20.0' })

    const version = await fetchBackendVersion()
    expect(version).toBe('0.20.0')
  })
})

describe('fetchLatestRelease', () => {
  it('returns the version with leading v stripped', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn<typeof fetch>()
        .mockResolvedValueOnce(
          new Response(JSON.stringify({ tag_name: 'v0.21.0', prerelease: false }), { status: 200 }),
        ),
    )
    const version = await fetchLatestRelease()
    expect(version).toBe('0.21.0')
    vi.unstubAllGlobals()
  })

  it('returns null when the latest release is a pre-release', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>().mockResolvedValueOnce(
        new Response(JSON.stringify({ tag_name: 'v0.22.0-beta1', prerelease: true }), {
          status: 200,
        }),
      ),
    )
    const version = await fetchLatestRelease()
    expect(version).toBeNull()
    vi.unstubAllGlobals()
  })

  it('returns null when the request fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>().mockResolvedValueOnce(new Response(null, { status: 404 })),
    )
    const version = await fetchLatestRelease()
    expect(version).toBeNull()
    vi.unstubAllGlobals()
  })

  it('returns null when fetch throws (offline)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>().mockRejectedValueOnce(new TypeError('Failed to fetch')),
    )
    const version = await fetchLatestRelease()
    expect(version).toBeNull()
    vi.unstubAllGlobals()
  })
})

describe('isPreRelease', () => {
  it('returns true for a pre-release version', () => {
    expect(isPreRelease('0.19.0-beta1')).toBe(true)
  })

  it('returns false for a stable version', () => {
    expect(isPreRelease('0.19.0')).toBe(false)
  })
})

describe('fetchLatestPreRelease', () => {
  it('returns the first pre-release tag with leading v stripped', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>().mockResolvedValueOnce(
        new Response(
          JSON.stringify([
            { tag_name: 'v0.19.0-beta2', prerelease: true },
            { tag_name: 'v0.18.3', prerelease: false },
          ]),
          { status: 200 },
        ),
      ),
    )
    const version = await fetchLatestPreRelease()
    expect(version).toBe('0.19.0-beta2')
    vi.unstubAllGlobals()
  })

  it('returns null when no pre-release exists in the list', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>().mockResolvedValueOnce(
        new Response(JSON.stringify([{ tag_name: 'v0.18.3', prerelease: false }]), {
          status: 200,
        }),
      ),
    )
    const version = await fetchLatestPreRelease()
    expect(version).toBeNull()
    vi.unstubAllGlobals()
  })

  it('returns null when the request fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>().mockResolvedValueOnce(new Response(null, { status: 500 })),
    )
    const version = await fetchLatestPreRelease()
    expect(version).toBeNull()
    vi.unstubAllGlobals()
  })
})
