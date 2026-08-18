import { useMutation, useQueryClient } from '@tanstack/vue-query'

import { queryKeys } from '@/services/queryKeys'
import { exportProfileData, importProfileData } from '@/features/profile/services/dataTransfer'

/**
 * Export mutation. Resolves with the export archive; the caller is responsible
 * for saving it (e.g. via `downloadBlob`). Modelled as a mutation purely for
 * the in-flight / error state — it changes no server state.
 *
 * @returns The TanStack Query mutation that produces the export blob.
 */
export function useExportProfileMutation() {
  return useMutation<Blob, Error, void>({
    mutationFn: () => exportProfileData(),
  })
}

/**
 * Import mutation. An import can create or replace data across many domains
 * (profile, activities, gear, health, notifications), so on settle it
 * invalidates each domain's broad cache plus the current-user shell so the
 * whole app reflects the imported state.
 *
 * @returns The TanStack Query mutation for importing a profile archive.
 */
export function useImportProfileMutation() {
  const client = useQueryClient()

  return useMutation<void, Error, File>({
    mutationFn: (file) => importProfileData(file),
    onSettled: () => {
      void client.invalidateQueries({ queryKey: queryKeys.profile.all() })
      void client.invalidateQueries({ queryKey: queryKeys.gears.all() })
      void client.invalidateQueries({ queryKey: queryKeys.activities.all() })
      void client.invalidateQueries({ queryKey: queryKeys.notifications.all() })
      void client.invalidateQueries({ queryKey: queryKeys.currentUser() })
    },
  })
}
