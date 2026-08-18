import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { RouteLocationNormalized } from 'vue-router'

const { isEnabled } = vi.hoisted(() => ({
  isEnabled: vi.fn<(flag: string) => boolean>(() => true),
}))

vi.mock('@/features/config/composables/useAppConfig', () => ({
  useFeatureFlags: () => ({ isEnabled }),
}))

import { authGuard } from '@/router'
import { useAuthStore } from '@/features/auth/stores/auth'
import { queryClient } from '@/plugins/vueQuery'
import { queryKeys } from '@/services/queryKeys'

/**
 * Builds a minimal route location for guard assertions.
 *
 * @param meta - Route meta flags under test.
 * @param fullPath - Target full path.
 * @returns A route location accepted by {@link authGuard}.
 */
function routeTo(meta: Record<string, unknown>, fullPath = '/target'): RouteLocationNormalized {
  return {
    fullPath,
    path: fullPath,
    name: 'target',
    meta,
    query: {},
    params: {},
    hash: '',
    matched: [],
    redirectedFrom: undefined,
  } as unknown as RouteLocationNormalized
}

describe('authGuard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    isEnabled.mockReturnValue(true)
  })

  afterEach(() => {
    // The query client is a singleton; drop any seeded current user between tests.
    queryClient.clear()
  })

  it('redirects unauthenticated users to login with a redirect query', async () => {
    const auth = useAuthStore()
    auth.isReady = true

    const result = await authGuard(routeTo({ requiresAuth: true }, '/activities'))

    expect(result).toEqual({ name: 'login', query: { redirect: '/activities' } })
  })

  it('allows authenticated users through protected routes', async () => {
    const auth = useAuthStore()
    auth.isReady = true
    auth.isAuthenticated = true

    const result = await authGuard(routeTo({ requiresAuth: true }))

    expect(result).toBe(true)
  })

  it('redirects authenticated users away from guest-only routes', async () => {
    const auth = useAuthStore()
    auth.isReady = true
    auth.isAuthenticated = true

    const result = await authGuard(routeTo({ requiresAuth: false, guestOnly: true }))

    expect(result).toEqual({ name: 'home' })
  })

  it('blocks routes whose feature flag is disabled', async () => {
    isEnabled.mockReturnValue(false)
    const auth = useAuthStore()
    auth.isReady = true
    auth.isAuthenticated = true

    const result = await authGuard(routeTo({ requiresAuth: false, feature: 'signUp' }))

    expect(result).toEqual({ name: 'home' })
    expect(isEnabled).toHaveBeenCalledWith('signUp')
  })

  it('allows administrators through admin-only routes', async () => {
    const auth = useAuthStore()
    auth.isReady = true
    auth.isAuthenticated = true
    queryClient.setQueryData(queryKeys.currentUser(), { accessType: 'admin' })

    const result = await authGuard(routeTo({ requiresAuth: true, requiresAdmin: true }))

    expect(result).toBe(true)
  })

  it('redirects non-administrators away from admin-only routes', async () => {
    const auth = useAuthStore()
    auth.isReady = true
    auth.isAuthenticated = true
    queryClient.setQueryData(queryKeys.currentUser(), { accessType: 'regular' })

    const result = await authGuard(routeTo({ requiresAuth: true, requiresAdmin: true }))

    expect(result).toEqual({ name: 'home' })
  })
})
