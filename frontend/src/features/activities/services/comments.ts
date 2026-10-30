import { apiFetch } from '@/services/http'

import type { ActivityComment, ActivityCommentDto } from '../types'

/**
 * Maps an activity-comment DTO to the camelCase domain model.
 *
 * @param dto - The comment wire payload.
 * @returns The comment domain model.
 */
export function mapActivityComment(dto: ActivityCommentDto): ActivityComment {
  return {
    id: dto.id,
    activityId: dto.activity_id,
    userId: dto.user_id,
    content: dto.content,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at ?? null,
  }
}

/**
 * Fetches the comment thread of an activity. Visible comments are the
 * ones the backend access check lets the requester see (owner, public,
 * or accepted-follower visibility).
 *
 * @param activityId - The commented activity id.
 * @param signal - Optional abort signal.
 * @returns The mapped comment thread (oldest first).
 */
export async function fetchActivityComments(
  activityId: number,
  signal?: AbortSignal,
): Promise<ActivityComment[]> {
  const dtos = await apiFetch<ActivityCommentDto[]>(
    `/activities_comments/activity_id/${activityId}`,
    {
      signal,
    },
  )
  return (dtos ?? []).map(mapActivityComment)
}

/**
 * Posts a comment to an activity the requester may see.
 *
 * @param activityId - The commented activity id.
 * @param content - The comment text (1-2000 chars, backend-validated).
 * @returns The created comment.
 */
export async function createActivityComment(
  activityId: number,
  content: string,
): Promise<ActivityComment> {
  const dto = await apiFetch<ActivityCommentDto>(`/activities_comments/activity_id/${activityId}`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  })
  return mapActivityComment(dto)
}

/**
 * Edits the requester's own comment.
 *
 * @param commentId - The comment id.
 * @param content - The new comment text.
 * @returns The updated comment.
 */
export async function updateActivityComment(
  commentId: number,
  content: string,
): Promise<ActivityComment> {
  const dto = await apiFetch<ActivityCommentDto>(`/activities_comments/${commentId}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  })
  return mapActivityComment(dto)
}

/**
 * Deletes a comment (its author or the activity owner).
 *
 * @param commentId - The comment id.
 */
export async function deleteActivityComment(commentId: number): Promise<void> {
  await apiFetch<void>(`/activities_comments/${commentId}`, { method: 'DELETE' })
}

/**
 * Comment count for one activity (feed badge). Returns 0 when the
 * activity is not visible or the request fails — the badge then hides.
 *
 * @param activityId - The activity id.
 * @returns The comment count.
 */
export async function fetchActivityCommentCount(activityId: number): Promise<number> {
  const dto = await apiFetch<{ activity_id: number; count: number }>(
    `/activities_comments/activity_id/${activityId}/count`,
  )
  return dto?.count ?? 0
}

/**
 * Batch comment counts for feed cards (one request instead of N+1).
 *
 * @param activityIds - Visible activity ids (capped at 100 server-side).
 * @returns Mapping activityId -> count (missing keys mean 0/hidden).
 */
export async function fetchActivityCommentCounts(
  activityIds: number[],
): Promise<Record<number, number>> {
  if (activityIds.length === 0) return {}
  const dto = await apiFetch<{ counts: Record<string, number> }>(`/activities_comments/counts`, {
    method: 'POST',
    body: JSON.stringify({ activity_ids: activityIds }),
  })
  const out: Record<number, number> = {}
  for (const [k, v] of Object.entries(dto?.counts ?? {})) {
    const id = Number(k)
    if (Number.isFinite(id)) out[id] = v
  }
  return out
}
