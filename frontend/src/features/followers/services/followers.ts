import type { FollowEdge, FollowerDto, FollowStatus } from '@/features/followers/types'
import type { Schemas } from '@/types'

import { apiFetch } from '@/services/http'

/**
 * Derives the viewer's {@link FollowStatus} from the raw relationship record
 * returned by the state endpoint (`null` when no relationship exists).
 *
 * @param dto - The viewer → target relationship, or `null`.
 * @returns `none` (no record), `pending` (unaccepted), or `accepted`.
 */
export function mapFollowStatus(dto: FollowerDto | null): FollowStatus {
  if (!dto) {
    return 'none'
  }
  return dto.is_accepted ? 'accepted' : 'pending'
}

/**
 * Fetches the people who follow a user (the user's followers list). Each row's
 * *other* user is the follower (`follower_id`).
 *
 * @param userId - The profile owner whose followers to load.
 * @param signal - Optional abort signal for cancellation.
 * @returns The follower edges (other user id + accepted flag).
 * @throws {HttpError} When the request fails.
 */
export async function fetchFollowers(userId: number, signal?: AbortSignal): Promise<FollowEdge[]> {
  const dtos = await apiFetch<FollowerDto[] | null>(`/followers/user/${userId}/followers/all`, {
    signal,
  })
  return (dtos ?? []).map((dto) => ({ userId: dto.follower_id, isAccepted: dto.is_accepted }))
}

/**
 * Fetches the people a user follows (the user's following list). Each row's
 * *other* user is the followed user (`following_id`).
 *
 * @param userId - The profile owner whose following list to load.
 * @param signal - Optional abort signal for cancellation.
 * @returns The following edges (other user id + accepted flag).
 * @throws {HttpError} When the request fails.
 */
export async function fetchFollowing(userId: number, signal?: AbortSignal): Promise<FollowEdge[]> {
  const dtos = await apiFetch<FollowerDto[] | null>(`/followers/user/${userId}/following/all`, {
    signal,
  })
  return (dtos ?? []).map((dto) => ({ userId: dto.following_id, isAccepted: dto.is_accepted }))
}

/**
 * Fetches a user's accepted-followers count (public-profile header).
 *
 * @param userId - The profile owner whose follower count to load.
 * @param signal - Optional abort signal for cancellation.
 * @returns The number of accepted followers.
 * @throws {HttpError} When the request fails.
 */
export async function fetchFollowersCount(userId: number, signal?: AbortSignal): Promise<number> {
  return apiFetch<number>(`/followers/user/${userId}/followers/count/accepted`, { signal })
}

/**
 * Fetches a user's accepted-following count (public-profile header).
 *
 * @param userId - The profile owner whose following count to load.
 * @param signal - Optional abort signal for cancellation.
 * @returns The number of users the profile owner follows (accepted).
 * @throws {HttpError} When the request fails.
 */
export async function fetchFollowingCount(userId: number, signal?: AbortSignal): Promise<number> {
  return apiFetch<number>(`/followers/user/${userId}/following/count/accepted`, { signal })
}

/**
 * Fetches the authenticated viewer's follow relationship to a target user,
 * backing the follow button's state.
 *
 * @param viewerId - The authenticated viewer's id.
 * @param targetId - The profile owner's id.
 * @param signal - Optional abort signal for cancellation.
 * @returns The viewer's {@link FollowStatus} for the target.
 * @throws {HttpError} When the request fails.
 */
export async function fetchFollowStatus(
  viewerId: number,
  targetId: number,
  signal?: AbortSignal,
): Promise<FollowStatus> {
  const dto = await apiFetch<FollowerDto | null>(
    `/followers/user/${viewerId}/targetUser/${targetId}`,
    { signal },
  )
  return mapFollowStatus(dto)
}

/**
 * Sends a follow request from the authenticated viewer to the target user.
 *
 * @param targetId - The user to follow.
 * @throws {HttpError} When the request fails.
 */
export async function followUser(targetId: number): Promise<void> {
  await apiFetch<FollowerDto>(`/followers/create/targetUser/${targetId}`, { method: 'POST' })
}

/**
 * Accepts a pending follow request from the target user (so they follow the
 * authenticated viewer).
 *
 * @param targetId - The requesting user to accept.
 * @throws {HttpError} When the request fails.
 */
export async function acceptFollower(targetId: number): Promise<void> {
  await apiFetch<Schemas['MessageResponse']>(`/followers/accept/targetUser/${targetId}`, {
    method: 'PUT',
  })
}

/**
 * Removes a user the authenticated viewer is following — i.e. unfollows the
 * target, or cancels a still-pending follow request to them.
 *
 * @param targetId - The followed (or requested) user to drop.
 * @throws {HttpError} When the request fails.
 */
export async function unfollowUser(targetId: number): Promise<void> {
  await apiFetch<Schemas['MessageResponse']>(`/followers/delete/follower/targetUser/${targetId}`, {
    method: 'DELETE',
  })
}

/**
 * Removes a follower of the authenticated viewer — i.e. declines a pending
 * request, or removes an existing accepted follower.
 *
 * @param targetId - The follower to remove.
 * @throws {HttpError} When the request fails.
 */
export async function removeFollower(targetId: number): Promise<void> {
  await apiFetch<Schemas['MessageResponse']>(`/followers/delete/following/targetUser/${targetId}`, {
    method: 'DELETE',
  })
}
