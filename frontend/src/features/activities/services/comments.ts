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
