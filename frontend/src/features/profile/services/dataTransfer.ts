import { apiFetch } from '@/services/http'

/**
 * Exports all of the authenticated user's profile data as a ZIP archive. The
 * timeout is disabled because a full export can take a while to stream.
 *
 * @param signal - Optional abort signal for cancellation.
 * @returns The export archive as a {@link Blob}.
 * @throws {HttpError} When the export fails.
 */
export function exportProfileData(signal?: AbortSignal): Promise<Blob> {
  return apiFetch<Blob>('/profile/export', { responseType: 'blob', timeoutMs: 0, signal })
}

/**
 * Imports profile data from a ZIP archive. The file is sent as multipart form
 * data under the `file` field; the backend validates it as a ZIP and processes
 * its contents, so the caller's filename never builds a path. The timeout is
 * disabled because importing can take a while.
 *
 * @param file - The ZIP archive to import.
 * @throws {HttpError} When the import fails (e.g. invalid archive).
 */
export async function importProfileData(file: File): Promise<void> {
  const formData = new FormData()
  formData.append('file', file, file.name)
  await apiFetch('/profile/import', {
    method: 'POST',
    body: formData,
    timeoutMs: 0,
    responseType: 'void',
  })
}
