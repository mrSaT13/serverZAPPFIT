import { describe, expect, it } from 'vitest'

import { isAdminUser } from '@/features/auth/composables/useCurrentUser'
import { accessibleSettingsZones } from '@/features/settings/settingsNav'

describe('isAdminUser', () => {
  it('is true only for users with admin access', () => {
    expect(isAdminUser({ accessType: 'admin' })).toBe(true)
    expect(isAdminUser({ accessType: 'regular' })).toBe(false)
    expect(isAdminUser(null)).toBe(false)
    expect(isAdminUser(undefined)).toBe(false)
  })
})

describe('accessibleSettingsZones', () => {
  it('exposes admin-only zones to administrators', () => {
    const zones = accessibleSettingsZones(true)
    expect(zones.some((zone) => zone.name === 'settings-profile')).toBe(true)
    expect(zones.some((zone) => zone.name === 'settings-goals')).toBe(true)
    expect(zones.some((zone) => zone.name === 'settings-security')).toBe(true)
    expect(zones.some((zone) => zone.name === 'settings-users')).toBe(true)
    expect(zones.some((zone) => zone.name === 'settings-idp')).toBe(true)
    expect(zones.some((zone) => zone.name === 'settings-server')).toBe(true)
  })

  it('hides admin-only zones from non-administrators but keeps the account zones', () => {
    const zones = accessibleSettingsZones(false)
    expect(zones.some((zone) => zone.name === 'settings-profile')).toBe(true)
    expect(zones.some((zone) => zone.name === 'settings-goals')).toBe(true)
    expect(zones.some((zone) => zone.name === 'settings-security')).toBe(true)
    expect(zones.every((zone) => !zone.adminOnly)).toBe(true)
    expect(zones.some((zone) => zone.name === 'settings-users')).toBe(false)
    expect(zones.some((zone) => zone.name === 'settings-idp')).toBe(false)
    expect(zones.some((zone) => zone.name === 'settings-server')).toBe(false)
  })

  it('lands non-admins on the profile zone and admins on the first admin zone', () => {
    // Non-admins only have the profile zone, so it is their default landing.
    expect(accessibleSettingsZones(false)[0]?.name).toBe('settings-profile')
    // Admins see admin zones first (admin-first order), so they land there.
    expect(accessibleSettingsZones(true)[0]?.adminOnly).toBe(true)
  })
})
