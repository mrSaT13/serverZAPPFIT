import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ServerSettingsDto, TileMapsTemplateDto } from '@/features/serverSettings/types'

import { apiFetch } from '@/services/http'
import {
  completeSetup,
  deleteLoginPhoto,
  fetchServerSettings,
  fetchSetupOptions,
  fetchSetupStatus,
  fetchTileMapsTemplates,
  mapServerSettings,
  mapTileMapsTemplate,
  toServerSettingsWire,
  updateServerSettings,
  uploadLoginPhoto,
} from '@/features/serverSettings/services/serverSettings'

vi.mock('@/services/http', () => ({
  apiFetch: vi.fn<typeof apiFetch>(),
}))

/** Builds a full `ServerSettingsRead` wire payload, overridable per case. */
function makeSettingsDto(overrides: Partial<ServerSettingsDto> = {}): ServerSettingsDto {
  return {
    id: 1,
    units: 'metric',
    currency: 'euro',
    num_records_per_page: 25,
    public_shareable_links: false,
    public_shareable_links_user_info: false,
    login_photo_set: true,
    signup_enabled: false,
    signup_require_admin_approval: true,
    signup_require_email_verification: true,
    sso_enabled: false,
    local_login_enabled: true,
    sso_auto_redirect: false,
    tileserver_url: 'https://tile.test/{z}/{x}/{y}.png',
    tileserver_attribution: '© Test',
    tileserver_api_key: 'secret-key',
    tileserver_regenerate_thumbnails_on_change: false,
    map_background_color: '#dddddd',
    password_type: 'strict',
    password_length_regular_users: 8,
    password_length_admin_users: 12,
    setup_completed: false,
    default_theme: 'system',
    default_language: 'en',
    brand_name: 'ZAPFIT',
    // smtp — new optional fields (not in generated type yet, cast via overrides)
    ...( {
      smtp_host: null,
      smtp_port: null,
      smtp_username: null,
      smtp_password: null,
      smtp_from: null,
      smtp_secure: null,
      smtp_secure_type: null,
    } as unknown as Partial<ServerSettingsDto>),
    ...overrides,
  } as unknown as ServerSettingsDto
}
}

/** Builds a full `TileMapsTemplate` wire payload, overridable per case. */
function makeTemplateDto(overrides: Partial<TileMapsTemplateDto> = {}): TileMapsTemplateDto {
  return {
    template_id: 'openstreetmap',
    name: 'OpenStreetMap',
    url_template: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '© OpenStreetMap',
    map_background_color: '#aad3df',
    requires_api_key_frontend: false,
    requires_api_key_backend: false,
    ...overrides,
  }
}

describe('mapServerSettings', () => {
  it('maps the wire shape to the clean camel-cased model', () => {
    expect(mapServerSettings(makeSettingsDto())).toEqual({
      id: 1,
      units: 'metric',
      currency: 'euro',
      numRecordsPerPage: 25,
      publicShareableLinks: false,
      publicShareableLinksUserInfo: false,
      loginPhotoSet: true,
      signupEnabled: false,
      signupRequireAdminApproval: true,
      signupRequireEmailVerification: true,
      ssoEnabled: false,
      localLoginEnabled: true,
      ssoAutoRedirect: false,
      tileserverUrl: 'https://tile.test/{z}/{x}/{y}.png',
      tileserverAttribution: '© Test',
      tileserverApiKey: 'secret-key',
      tileserverRegenerateThumbnailsOnChange: false,
      mapBackgroundColor: '#dddddd',
      passwordType: 'strict',
      passwordLengthRegularUsers: 8,
      passwordLengthAdminUsers: 12,
      setupCompleted: false,
      defaultTheme: 'system',
      defaultLanguage: 'en',
      brandName: 'ZAPFIT',
      smtpHost: null,
      smtpPort: null,
      smtpUsername: null,
      smtpPassword: null,
      smtpFrom: null,
      smtpSecure: null,
      smtpSecureType: null,
    })
  })

  it('normalizes a missing API key to null', () => {
    expect(
      mapServerSettings(makeSettingsDto({ tileserver_api_key: null })).tileserverApiKey,
    ).toBeNull()
  })
})

describe('mapTileMapsTemplate', () => {
  it('maps the wire shape to the clean model', () => {
    expect(mapTileMapsTemplate(makeTemplateDto())).toEqual({
      templateId: 'openstreetmap',
      name: 'OpenStreetMap',
      urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution: '© OpenStreetMap',
      mapBackgroundColor: '#aad3df',
      requiresApiKeyFrontend: false,
      requiresApiKeyBackend: false,
    })
  })
})

describe('toServerSettingsWire', () => {
  it('round-trips every editable field so the full record is replaced', () => {
    const settings = mapServerSettings(makeSettingsDto())
    // `setup_completed` is read-only (never sent on write) — exclude it.
    const { setup_completed: _setupCompleted, ...expected } = makeSettingsDto()
    expect(toServerSettingsWire(settings)).toEqual(expected)
  })
})

describe('server settings service requests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchServerSettings reads the admin endpoint and maps the response', async () => {
    vi.mocked(apiFetch).mockResolvedValue(makeSettingsDto())

    const settings = await fetchServerSettings()

    expect(apiFetch).toHaveBeenCalledWith('/server_settings', { signal: undefined })
    expect(settings.numRecordsPerPage).toBe(25)
  })

  it('fetchTileMapsTemplates maps the list and tolerates a null payload', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce([makeTemplateDto()])
    expect(await fetchTileMapsTemplates()).toHaveLength(1)
    expect(apiFetch).toHaveBeenCalledWith('/server_settings/tile_maps_templates', {
      signal: undefined,
    })

    vi.mocked(apiFetch).mockResolvedValueOnce(null)
    expect(await fetchTileMapsTemplates()).toEqual([])
  })

  it('updateServerSettings PUTs the full wire body', async () => {
    vi.mocked(apiFetch).mockResolvedValue(makeSettingsDto())
    const settings = mapServerSettings(makeSettingsDto({ signup_enabled: true }))

    await updateServerSettings(settings)

    expect(apiFetch).toHaveBeenCalledWith('/server_settings', {
      method: 'PUT',
      body: JSON.stringify(toServerSettingsWire(settings)),
    })
  })

  it('uploadLoginPhoto posts the file as multipart form data', async () => {
    let capturedBody: unknown
    vi.mocked(apiFetch).mockImplementation((_path, init) => {
      capturedBody = init?.body
      return Promise.resolve(undefined)
    })
    const file = new File(['x'], 'login.png', { type: 'image/png' })

    await uploadLoginPhoto(file)

    expect(apiFetch).toHaveBeenCalledWith(
      '/server_settings/upload/login',
      expect.objectContaining({ method: 'POST', responseType: 'void' }),
    )
    expect(capturedBody).toBeInstanceOf(FormData)
    expect((capturedBody as FormData).get('file')).toBe(file)
  })

  it('deleteLoginPhoto issues a DELETE', async () => {
    vi.mocked(apiFetch).mockResolvedValue(undefined)

    await deleteLoginPhoto()

    expect(apiFetch).toHaveBeenCalledWith('/server_settings/upload/login', {
      method: 'DELETE',
      responseType: 'void',
    })
  })

  it('fetchSetupStatus reads the public endpoint and maps the response', async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      setup_completed: false,
      brand_name: 'ZAPFIT',
    })

    const status = await fetchSetupStatus()

    expect(apiFetch).toHaveBeenCalledWith('/public/server_settings/setup-status', {
      signal: undefined,
    })
    expect(status).toEqual({ setupCompleted: false, brandName: 'ZAPFIT' })
  })

  it('fetchSetupOptions reads the public endpoint and normalizes options', async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      themes: [{ value: 'dark', label: 'Dark' }],
      languages: [{ code: 'ru', label: 'Русский' }],
      brand_name: 'ZAPFIT',
    })

    const options = await fetchSetupOptions()

    expect(apiFetch).toHaveBeenCalledWith('/public/server_settings/setup-options', {
      signal: undefined,
    })
    expect(options).toEqual({
      themes: [{ value: 'dark', label: 'Dark' }],
      languages: [{ code: 'ru', label: 'Русский' }],
      brandName: 'ZAPFIT',
    })
  })

  it('completeSetup POSTs the full wire body to the setup endpoint', async () => {
    vi.mocked(apiFetch).mockResolvedValue(makeSettingsDto())
    const settings = mapServerSettings(makeSettingsDto({ default_theme: 'dark' }))

    await completeSetup(settings)

    const wire = toServerSettingsWire(settings)
    expect(apiFetch).toHaveBeenCalledWith('/server_settings/setup-complete', {
      method: 'POST',
      body: JSON.stringify(wire),
    })
  })
})
