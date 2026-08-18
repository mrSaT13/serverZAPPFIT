import { storeToRefs } from 'pinia'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'

import type { ServerSettings } from '@/features/serverSettings/types'

import { queryKeys } from '@/services/queryKeys'
import { useAuthStore } from '@/features/auth/stores/auth'
import {
  completeSetup,
  deleteLoginPhoto,
  fetchServerSettings,
  fetchSetupOptions,
  fetchSetupStatus,
  fetchTileMapsTemplates,
  updateServerSettings,
  uploadLoginPhoto,
} from '@/features/serverSettings/services/serverSettings'

/**
 * The singleton server settings (admin scope). Gated on authentication; the
 * route guard already restricts the page to admins, so this only needs the
 * auth gate to avoid firing before a session exists.
 *
 * @returns The TanStack Query result for the server settings.
 */
export function useServerSettingsQuery() {
  const { isAuthenticated } = storeToRefs(useAuthStore())

  return useQuery({
    queryKey: queryKeys.serverSettings.detail(),
    queryFn: ({ signal }) => fetchServerSettings(signal),
    enabled: isAuthenticated,
  })
}

/**
 * The static catalogue of tile-server presets. Cached indefinitely
 * (`staleTime: Infinity`) since the list is build-time constant on the backend.
 *
 * @returns The TanStack Query result for the tile-map presets.
 */
export function useTileMapsTemplatesQuery() {
  const { isAuthenticated } = storeToRefs(useAuthStore())

  return useQuery({
    queryKey: queryKeys.serverSettings.tileTemplates(),
    queryFn: ({ signal }) => fetchTileMapsTemplates(signal),
    enabled: isAuthenticated,
    staleTime: Number.POSITIVE_INFINITY,
  })
}

/**
 * Invalidates both the admin server-settings cache and the public settings
 * cache. Server settings drive unauthenticated surfaces too (the login screen's
 * photo, the list page size via `useRecordsPerPage`), so a write must refresh
 * both or those views go stale until reload.
 *
 * @param client - The active query client.
 */
function invalidateServerSettings(client: ReturnType<typeof useQueryClient>): void {
  void client.invalidateQueries({ queryKey: queryKeys.serverSettings.all() })
  void client.invalidateQueries({ queryKey: queryKeys.public.serverSettings() })
}

/**
 * Update mutation for the whole server-settings record. Invalidates the admin
 * and public caches on settle so the form, the login screen, and paginated
 * lists all pick up the new values.
 *
 * @returns The TanStack Query mutation for updating server settings.
 */
export function useUpdateServerSettingsMutation() {
  const client = useQueryClient()

  return useMutation<ServerSettings, Error, ServerSettings>({
    mutationKey: queryKeys.serverSettings.all(),
    mutationFn: (settings) => updateServerSettings(settings),
    onSettled: () => invalidateServerSettings(client),
  })
}

/**
 * Login-photo upload mutation. Invalidates the admin and public caches so the
 * "photo set" state and the login screen refresh.
 *
 * @returns The TanStack Query mutation for uploading the login photo.
 */
export function useUploadLoginPhotoMutation() {
  const client = useQueryClient()

  return useMutation<void, Error, File>({
    mutationKey: queryKeys.serverSettings.all(),
    mutationFn: (file) => uploadLoginPhoto(file),
    onSettled: () => invalidateServerSettings(client),
  })
}

/**
 * Login-photo deletion mutation. Invalidates the same caches as the upload.
 *
 * @returns The TanStack Query mutation for removing the login photo.
 */
export function useDeleteLoginPhotoMutation() {
  const client = useQueryClient()

  return useMutation<void, Error, void>({
    mutationKey: queryKeys.serverSettings.all(),
    mutationFn: () => deleteLoginPhoto(),
    onSettled: () => invalidateServerSettings(client),
  })
}

/**
 * Public setup-wizard status (does the first-time wizard still need to run?).
 * Not gated on auth: the login page reads it to decide the post-login redirect.
 *
 * @returns The TanStack Query result for the setup status.
 */
export function useSetupStatusQuery() {
  return useQuery({
    queryKey: queryKeys.serverSettings.setupStatus(),
    queryFn: ({ signal }) => fetchSetupStatus(signal),
    staleTime: Number.POSITIVE_INFINITY,
  })
}

/**
 * Static theme/language options for the first-time setup wizard. Cached
 * indefinitely since the list is build-time constant on the backend.
 *
 * @returns The TanStack Query result for the setup options.
 */
export function useSetupOptionsQuery() {
  return useQuery({
    queryKey: queryKeys.serverSettings.setupOptions(),
    queryFn: ({ signal }) => fetchSetupOptions(signal),
    staleTime: Number.POSITIVE_INFINITY,
  })
}

/**
 * Setup-wizard completion mutation. Applies the full server configuration in
 * one round-trip and marks the wizard done. Invalidates the admin and public
 * settings caches plus the setup-status key so the whole app sees the change.
 *
 * @returns The TanStack Query mutation for completing the setup.
 */
export function useCompleteSetupMutation() {
  const client = useQueryClient()

  return useMutation<ServerSettings, Error, ServerSettings>({
    mutationKey: queryKeys.serverSettings.setupStatus(),
    mutationFn: (settings) => completeSetup(settings),
    onSettled: () => {
      invalidateServerSettings(client)
      void client.invalidateQueries({ queryKey: queryKeys.serverSettings.setupStatus() })
    },
  })
}
