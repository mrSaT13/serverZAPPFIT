import { beforeEach, describe, expect, it, vi } from 'vitest'

import { HttpError } from '@/services/http'
import { DEFAULT_APP_CONFIG, fetchAppConfig } from '@/features/config/services/config'
import { loadAppConfig, useAppConfig } from '@/features/config/composables/useAppConfig'

vi.mock('@/features/config/services/config', async (importActual) => {
  const actual = await importActual<typeof import('@/features/config/services/config')>()
  return { ...actual, fetchAppConfig: vi.fn<typeof actual.fetchAppConfig>() }
})

vi.mock('@/composables/useTelemetry', () => ({
  useTelemetry: () => ({ captureError: vi.fn<() => void>() }),
}))

describe('loadAppConfig configuration-error detection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('raises configError when the backend host is unreachable (non-HTTP failure)', async () => {
    vi.mocked(fetchAppConfig).mockRejectedValueOnce(new TypeError('Failed to fetch'))

    await loadAppConfig()

    expect(useAppConfig().configError.value).toBe(true)
  })

  it('raises configError when the request times out', async () => {
    vi.mocked(fetchAppConfig).mockRejectedValueOnce(
      new DOMException('The operation timed out.', 'TimeoutError'),
    )

    await loadAppConfig()

    expect(useAppConfig().configError.value).toBe(true)
  })

  it('stays quiet when the backend is reachable but answers with an HTTP error', async () => {
    vi.mocked(fetchAppConfig).mockRejectedValueOnce(new HttpError(500, 'Internal Server Error'))

    await loadAppConfig()

    expect(useAppConfig().configError.value).toBe(false)
  })

  it('clears a previous config error once the backend becomes reachable', async () => {
    vi.mocked(fetchAppConfig).mockRejectedValueOnce(new TypeError('Failed to fetch'))
    await loadAppConfig()
    expect(useAppConfig().configError.value).toBe(true)

    vi.mocked(fetchAppConfig).mockResolvedValueOnce(DEFAULT_APP_CONFIG)
    await loadAppConfig()
    expect(useAppConfig().configError.value).toBe(false)
  })
})
