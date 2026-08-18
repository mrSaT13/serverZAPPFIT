import type { PublicUser, UserDto } from '@/features/users/types'

import { resolveAvatarUrl } from '@/features/auth/services/mappers'
import { apiFetch } from '@/services/http'

/**
 * Maps a raw `UsersRead` payload to the privacy-conscious {@link PublicUser}
 * model shown on the public profile page, resolving the servable avatar URL
 * from the stored photo path and dropping every sensitive field.
 *
 * @param dto - Raw user payload from the backend.
 * @returns The normalized public-user model.
 */
export function mapPublicUser(dto: UserDto): PublicUser {
  return {
    id: dto.id,
    name: dto.name,
    username: dto.username,
    city: dto.city ?? null,
    avatarUrl: resolveAvatarUrl(dto.photo_path),
  }
}

/**
 * Fetches a user's public-facing profile for the `/user/:id` page. The route is
 * authenticated, so this uses the authenticated user endpoint (the same one
 * activity feeds use to resolve other users), which any signed-in viewer may
 * call — not the admin users-list scope.
 *
 * @param userId - The profile owner's id.
 * @param signal - Optional abort signal (e.g. TanStack Query cancellation).
 * @returns The public user, or `null` when not found.
 * @throws {HttpError} When the request fails.
 */
export async function fetchPublicUser(
  userId: number,
  signal?: AbortSignal,
): Promise<PublicUser | null> {
  const dto = await apiFetch<UserDto | null>(`/users/id/${userId}`, { signal })
  return dto ? mapPublicUser(dto) : null
}
