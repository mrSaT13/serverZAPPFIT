import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiFetch } from '@/services/http'
import { exportProfileData, importProfileData } from '@/features/profile/services/dataTransfer'

vi.mock('@/services/http', () => ({
  apiFetch: vi.fn<typeof apiFetch>(),
}))

describe('data transfer service requests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('exportProfileData requests the export as a blob with no timeout', async () => {
    const blob = new Blob(['archive'])
    vi.mocked(apiFetch).mockResolvedValue(blob)

    const result = await exportProfileData()

    expect(apiFetch).toHaveBeenCalledWith('/profile/export', {
      responseType: 'blob',
      timeoutMs: 0,
      signal: undefined,
    })
    expect(result).toBe(blob)
  })

  it('importProfileData posts the archive as multipart form data', async () => {
    let body: unknown
    vi.mocked(apiFetch).mockImplementation((_path, init) => {
      body = init?.body
      return Promise.resolve(undefined)
    })
    const file = new File(['x'], 'export.zip', { type: 'application/zip' })

    await importProfileData(file)

    expect(apiFetch).toHaveBeenCalledWith(
      '/profile/import',
      expect.objectContaining({ method: 'POST', timeoutMs: 0, responseType: 'void' }),
    )
    expect(body).toBeInstanceOf(FormData)
    const uploaded = (body as FormData).get('file')
    expect(uploaded).toBeInstanceOf(File)
    expect((uploaded as File).name).toBe('export.zip')
  })
})
