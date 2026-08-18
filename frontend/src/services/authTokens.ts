let accessToken: string | null = null
let csrfToken: string | null = null

/**
 * Returns the current in-memory bearer access token.
 *
 * @returns The access token, or `null` when unauthenticated.
 */
export function getAccessToken(): string | null {
  return accessToken
}

/**
 * Returns the current in-memory CSRF token bound to the refresh session.
 *
 * @returns The CSRF token, or `null` before login/refresh.
 */
export function getCsrfToken(): string | null {
  return csrfToken
}

/**
 * Stores auth tokens in memory only.
 *
 * @param nextAccessToken - Bearer token returned by the backend.
 * @param nextCsrfToken - CSRF token returned by the backend for web clients.
 */
export function setAuthTokens(nextAccessToken: string, nextCsrfToken: string): void {
  accessToken = nextAccessToken
  csrfToken = nextCsrfToken
}

/**
 * Clears all in-memory auth tokens.
 */
export function clearAuthTokens(): void {
  accessToken = null
  csrfToken = null
}
