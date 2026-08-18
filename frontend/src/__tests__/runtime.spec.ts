import { beforeEach, describe, expect, it } from 'vitest'

import { getApiBaseUrl, getBackendAssetUrl } from '@/services/runtime'

describe('runtime backend configuration', () => {
  beforeEach(() => {
    window.env = undefined
  })

  it('uses ZAPFIT_HOST from env.js for API calls', () => {
    window.env = { ZAPFIT_HOST: 'https://zapfit.example.test/' }

    expect(getApiBaseUrl()).toBe('https://zapfit.example.test/api/v1')
  })

  it('uses ZAPFIT_HOST from env.js for backend assets', () => {
    window.env = { ZAPFIT_HOST: 'https://zapfit.example.test' }

    expect(getBackendAssetUrl('/server_images/login.png')).toBe(
      'https://zapfit.example.test/server_images/login.png',
    )
  })

  it('falls back to ENDURAIN_HOST for backwards compatibility', () => {
    window.env = { ENDURAIN_HOST: 'https://legacy.example.test/' }

    expect(getApiBaseUrl()).toBe('https://legacy.example.test/api/v1')
  })
})
