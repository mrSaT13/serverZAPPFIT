const PREFIX = 'endurain:'
const DEVICE_SCOPED_KEYS = new Set([`${PREFIX}theme`, `${PREFIX}locale`])

/**
 * Reads and JSON-parses a namespaced value from `localStorage`.
 *
 * @param key - The unprefixed storage key.
 * @returns The parsed value, or `null` when absent, unparsable, or
 *   `localStorage` is unavailable (private mode, SSR).
 */
export function getStorageItem<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(PREFIX + key)
    return raw === null ? null : (JSON.parse(raw) as T)
  } catch {
    return null
  }
}

/**
 * JSON-serializes and writes a namespaced value to `localStorage`.
 *
 * @param key - The unprefixed storage key.
 * @param value - The value to persist.
 */
export function setStorageItem<T>(key: string, value: T): void {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value))
  } catch {
    // Storage may be unavailable or full; persistence is best-effort.
  }
}

/**
 * Removes a namespaced value from `localStorage`.
 *
 * @param key - The unprefixed storage key.
 */
export function removeStorageItem(key: string): void {
  try {
    localStorage.removeItem(PREFIX + key)
  } catch {
    // Ignore — nothing to clean up if storage is unavailable.
  }
}

/**
 * Clears every namespaced key. Intended for logout / tenant switches so one
 * user's cached state never leaks into another session.
 */
export function clearNamespacedStorage(): void {
  try {
    const keys = Object.keys(localStorage).filter((key) => key.startsWith(PREFIX))
    for (const key of keys) {
      localStorage.removeItem(key)
    }
  } catch {
    // Ignore — storage unavailable.
  }
}

/**
 * Clears user-scoped local data while preserving device preferences such as
 * theme and locale across logout/session expiry.
 */
export function clearUserScopedStorage(): void {
  try {
    const keys = Object.keys(localStorage).filter(
      (key) => key.startsWith(PREFIX) && !DEVICE_SCOPED_KEYS.has(key),
    )
    for (const key of keys) {
      localStorage.removeItem(key)
    }
  } catch {
    // Ignore — storage unavailable.
  }
}
