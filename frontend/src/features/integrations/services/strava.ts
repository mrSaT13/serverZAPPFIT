import type { DateRange, StravaClientDto, StravaClientInput } from '@/features/integrations/types'

import { apiFetch } from '@/services/http'
import { getRuntimeBackendHost } from '@/services/runtime'

/** The OAuth scopes Endurain requests from Strava (read-only access). */
const STRAVA_SCOPE = 'read,read_all,profile:read_all,activity:read,activity:read_all'

/**
 * Stores a one-time CSRF `state` on the user's Strava integration so the OAuth
 * callback can be correlated back to this account. Pass `null` to clear it.
 *
 * @param state - The opaque state value, or `null` to clear.
 * @throws {HttpError} When the request fails.
 */
export async function setStravaState(state: string | null): Promise<void> {
  await apiFetch(`/strava/state/${encodeURIComponent(state ?? 'null')}`, {
    method: 'PUT',
    responseType: 'void',
  })
}

/**
 * Stores the user's Strava API client id + secret ahead of the OAuth round-trip.
 *
 * @param input - The Strava application's client id and secret.
 * @throws {HttpError} When the request fails.
 */
export async function setStravaClient(input: StravaClientInput): Promise<void> {
  const payload: StravaClientDto = {
    client_id: input.clientId,
    client_secret: input.clientSecret,
  }
  await apiFetch('/strava/client', {
    method: 'PUT',
    body: JSON.stringify(payload),
    responseType: 'void',
  })
}

/**
 * Builds the Strava OAuth authorization URL the browser is sent to (full-page).
 * Strava redirects back to `{host}/strava/callback` with `code` + `state`.
 *
 * @param state - The CSRF state previously stored via {@link setStravaState}.
 * @param clientId - The Strava application's client id.
 * @returns The absolute Strava authorize URL.
 */
export function buildStravaAuthUrl(state: string, clientId: number): string {
  const host = getRuntimeBackendHost() ?? window.location.origin
  const redirectUri = encodeURIComponent(`${host}/strava/callback`)
  return (
    `https://www.strava.com/oauth/authorize?client_id=${clientId}` +
    `&response_type=code&redirect_uri=${redirectUri}&approval_prompt=force` +
    `&scope=${STRAVA_SCOPE}&state=${encodeURIComponent(state)}`
  )
}

/**
 * Completes the Strava link by exchanging the OAuth `code` for tokens. Called
 * from the `/strava/callback` view after Strava redirects back.
 *
 * @param state - The state echoed back by Strava.
 * @param code - The authorization code from Strava.
 * @throws {HttpError} When the exchange fails (e.g. 424 link failure).
 */
export async function completeStravaLink(state: string, code: string): Promise<void> {
  await apiFetch(
    `/strava/link?state=${encodeURIComponent(state)}&code=${encodeURIComponent(code)}`,
    {
      method: 'PUT',
      responseType: 'void',
    },
  )
}

/**
 * Kicks off a background import of Strava activities in the given date window.
 * The work runs server-side; progress arrives over the realtime channel.
 *
 * @param range - The inclusive date window to import.
 * @throws {HttpError} When the request fails.
 */
export async function retrieveStravaActivities(range: DateRange): Promise<void> {
  await apiFetch(
    `/strava/activities?start_date=${encodeURIComponent(range.startDate)}&end_date=${encodeURIComponent(range.endDate)}`,
    { responseType: 'void' },
  )
}

/**
 * Kicks off a background import of the user's Strava gear.
 *
 * @throws {HttpError} When the request fails.
 */
export async function retrieveStravaGear(): Promise<void> {
  await apiFetch('/strava/gear', { responseType: 'void' })
}

/**
 * Disconnects the user's Strava account.
 *
 * @throws {HttpError} When the request fails.
 */
export async function unlinkStrava(): Promise<void> {
  await apiFetch('/strava/unlink', { method: 'DELETE', responseType: 'void' })
}
