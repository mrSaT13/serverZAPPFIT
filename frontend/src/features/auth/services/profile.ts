import type { User, UserProfileDto } from '@/features/auth/types'

import { apiFetch } from '@/services/http'
import { mapUserProfile } from './mappers'

/**
 * Fetches and normalizes the authenticated user's profile.
 *
 * @param signal - Optional abort signal so callers (e.g. TanStack Query) can
 *   cancel the request when a component unmounts or a query is invalidated.
 * @returns The current authenticated user, mapped to the clean {@link User} model.
 * @throws {HttpError} When the access token is invalid or the profile cannot be loaded.
 */
export async function fetchCurrentUser(signal?: AbortSignal): Promise<User> {
  return mapUserProfile(await apiFetch<UserProfileDto>('/profile', { signal }))
}
