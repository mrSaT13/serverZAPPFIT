/**
 * Decouples the HTTP layer from the auth store so a terminal token-refresh
 * failure can drop the session and redirect, without the low-level fetch code
 * importing the store (which would create an import cycle). Mirrors the
 * telemetry-adapter pattern: one handler, registered once during bootstrap.
 */
type SessionExpiredHandler = () => void

let handler: SessionExpiredHandler | null = null

/**
 * Registers the handler invoked when the session expires mid-flight. Call once
 * during bootstrap; pass `null` to clear (e.g. in tests).
 *
 * @param next - The handler to install, or `null` to remove it.
 */
export function onSessionExpired(next: SessionExpiredHandler | null): void {
  handler = next
}

/**
 * Signals that an authenticated session has expired and could not be renewed.
 * No-op when no handler is registered.
 */
export function emitSessionExpired(): void {
  handler?.()
}
