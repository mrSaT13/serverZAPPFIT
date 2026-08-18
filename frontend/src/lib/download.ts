/**
 * Triggers a browser download for an in-memory {@link Blob} (e.g. a generated
 * export archive). Creates a temporary object URL and a hidden anchor, clicks
 * it, then revokes the URL so the blob can be garbage-collected.
 *
 * @param blob - The binary payload to save.
 * @param filename - The suggested download filename.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.rel = 'noopener'
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
