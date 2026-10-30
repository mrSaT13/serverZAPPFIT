import { computed, type MaybeRefOrGetter, toValue } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'

import { queryKeys } from '@/services/queryKeys'

import {
  createActivityComment,
  deleteActivityComment,
  fetchActivityCommentCount,
  fetchActivityComments,
  updateActivityComment,
} from '../services/comments'
import type { ActivityComment } from '../types'

/** Resolves a reactive activity id into a non-negative number. */
function resolveId(id: MaybeRefOrGetter<number | null | undefined>): number {
  return toValue(id) ?? 0
}

/**
 * Loads the comment thread of an activity. Lazy: only fetches when the
 * caller opts in (comments are collapsed in the feed by default).
 *
 * @param id - Reactive activity id.
 * @param enabled - Reactive gate (typically "thread expanded").
 * @returns The TanStack query result; data is `[]` while closed.
 */
export function useActivityCommentsQuery(
  id: MaybeRefOrGetter<number | null | undefined>,
  enabled: MaybeRefOrGetter<boolean>,
) {
  return useQuery({
    queryKey: computed(() => queryKeys.activities.comments(resolveId(id))),
    queryFn: ({ signal }) => fetchActivityComments(resolveId(id), signal),
    enabled: computed(() => toValue(enabled) === true && resolveId(id) > 0),
    staleTime: 30_000,
  })
}

/**
 * Comment count badge for a feed card. Cheap `COUNT(*)` query, always
 * enabled while the card is visible — the toggle shows the number without
 * loading the whole thread.
 *
 * @param id - Reactive activity id.
 * @returns The TanStack query result; data is `0` while loading.
 */
export function useActivityCommentCountQuery(id: MaybeRefOrGetter<number | null | undefined>) {
  return useQuery({
    queryKey: computed(() => [...queryKeys.activities.comments(resolveId(id)), 'count'] as const),
    queryFn: () => fetchActivityCommentCount(resolveId(id)),
    enabled: computed(() => resolveId(id) > 0),
    staleTime: 30_000,
  })
}

/**
 * Posts a comment and refetches the thread.
 *
 * @returns The TanStack mutation result.
 */
export function useCreateActivityComment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ activityId, content }: { activityId: number; content: string }) =>
      createActivityComment(activityId, content),
    onSuccess: (comment: ActivityComment) => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.activities.comments(comment.activityId),
      })
      void queryClient.invalidateQueries({
        queryKey: [...queryKeys.activities.comments(comment.activityId), 'count'],
      })
    },
  })
}

/**
 * Edits an existing comment and refetches the thread.
 *
 * @returns The TanStack mutation result.
 */
export function useUpdateActivityComment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ commentId, content }: { commentId: number; content: string }) =>
      updateActivityComment(commentId, content),
    onSuccess: (comment: ActivityComment) => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.activities.comments(comment.activityId),
      })
    },
  })
}

/**
 * Deletes a comment and refetches the thread.
 *
 * @returns The TanStack mutation result.
 */
export function useDeleteActivityComment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ activityId, commentId }: { activityId: number; commentId: number }) =>
      deleteActivityComment(commentId).then(() => activityId),
    onSuccess: (activityId: number) => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.activities.comments(activityId),
      })
      void queryClient.invalidateQueries({
        queryKey: [...queryKeys.activities.comments(activityId), 'count'],
      })
    },
  })
}
