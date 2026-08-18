import { storeToRefs } from 'pinia'
import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import type { User } from '@/features/auth/types'

import { queryKeys } from '@/services/queryKeys'
import { fetchCurrentUser } from '@/features/auth/services/profile'
import { useAuthStore } from '@/features/auth/stores/auth'

/** The access tier that grants administrative privileges. */
export const ADMIN_ACCESS_TYPE = 'admin'

/**
 * Whether a user holds administrative access. Centralised so the admin check
 * is identical wherever it is made (nav, route guard).
 *
 * @param user - The user to check, or `null`/`undefined`.
 * @returns Whether the user is an administrator.
 */
export function isAdminUser(user: Pick<User, 'accessType'> | null | undefined): boolean {
  return user?.accessType === ADMIN_ACCESS_TYPE
}

/**
 * Canonical read path for the authenticated user. Reads the profile through
 * TanStack Query so views inherit caching, request de-duplication, background
 * refetch, and automatic cancellation — and so a profile update that
 * invalidates {@link queryKeys.currentUser} propagates everywhere at once.
 *
 * The auth store seeds this query's cache on login/restore, so mounting a view
 * that calls this does not trigger a redundant fetch. This is the only place
 * components should read the current user from; the store owns session state,
 * not the user object.
 *
 * @returns The TanStack Query result for the current user.
 */
export function useCurrentUser() {
  const auth = useAuthStore()
  const { isAuthenticated } = storeToRefs(auth)

  return useQuery<User>({
    queryKey: queryKeys.currentUser(),
    // `signal` is supplied by TanStack Query and forwarded to `fetch`, so
    // unmounting or navigating away aborts the in-flight request.
    queryFn: ({ signal }) => fetchCurrentUser(signal),
    enabled: isAuthenticated,
    staleTime: 60_000,
  })
}

/**
 * Reactive admin flag derived from the cached current user. Use in components
 * (e.g. settings navigation) to show or hide admin-only affordances; route
 * access is enforced separately by the router guard.
 *
 * @returns A reactive boolean that is `true` for administrators.
 */
export function useIsAdmin() {
  const { data } = useCurrentUser()
  return computed(() => isAdminUser(data.value))
}
