import { computed, type MaybeRefOrGetter, toValue } from 'vue'
import { storeToRefs } from 'pinia'
import { useQuery } from '@tanstack/vue-query'

import type { PublicUser } from '@/features/users/types'

import { queryKeys } from '@/services/queryKeys'
import { useAuthStore } from '@/features/auth/stores/auth'
import { fetchPublicUser } from '@/features/users/services/publicUsers'

/** Resolves a reactive user id to a positive number, or `0` when unavailable. */
function resolveUserId(userId: MaybeRefOrGetter<number | null>): number {
  const value = toValue(userId)
  return value !== null && Number.isFinite(value) && value > 0 ? value : 0
}

/**
 * A user's public-facing profile, backing the `/user/:id` page header and every
 * follower/following list row (deduplicated by id through the shared cache key).
 * Gated on a valid user id and authentication.
 *
 * @param userId - Reactive id of the user to load.
 * @returns The TanStack query result for the public user (`null` when missing).
 */
export function usePublicUserQuery(userId: MaybeRefOrGetter<number | null>) {
  const { isAuthenticated } = storeToRefs(useAuthStore())
  const id = computed(() => resolveUserId(userId))

  return useQuery<PublicUser | null>({
    queryKey: computed(() => queryKeys.users.publicProfile(id.value)),
    queryFn: ({ signal }) => fetchPublicUser(id.value, signal),
    enabled: computed(() => isAuthenticated.value && id.value > 0),
    staleTime: 5 * 60_000,
  })
}
