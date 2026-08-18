import { useMutation, useQueryClient } from '@tanstack/vue-query'

import { uploadActivityFile } from '@/features/upload/services/upload'
import type { Activity } from '@/features/upload/types'
import { queryKeys } from '@/services/queryKeys'

/**
 * Write-path reference for file uploads: a TanStack mutation that uploads one
 * activity file and, on success or failure, invalidates the activities domain
 * so any list view refetches the server-authoritative rows.
 *
 * Mirrors the mutation shape in
 * `@/features/notifications/composables/useNotifications`
 * (`mutationFn` + `onSettled` invalidation) — minus optimistic updates. An
 * upload's result (the parsed activities) is computed server-side and can't be
 * predicted on the client, so there is nothing to optimistically render; we
 * simply invalidate once the server responds.
 *
 * @returns The TanStack mutation. Call `mutate(file)` / `mutateAsync(file)`.
 */
export function useUploadActivityFileMutation() {
  const queryClient = useQueryClient()

  return useMutation<Activity[], Error, File>({
    mutationFn: (file) => uploadActivityFile(file),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.activities.all() })
    },
  })
}
