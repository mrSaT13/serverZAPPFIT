import type { ActivityStream, HrZoneBucket } from '../types'
import { STREAM_TYPE } from '../types'

/**
 * The five-zone heart-rate colour ramp (blue → green → amber → orange → red),
 * aligned to the design tokens. Indexed by zone − 1.
 */
export const HR_ZONE_COLORS: readonly string[] = [
  '#378add', // Zone 1 — info blue
  '#639922', // Zone 2 — goal green
  '#ef9f27', // Zone 3 — effort amber
  '#f97316', // Zone 4 — orange
  '#e24b4a', // Zone 5 — hr red
]

/**
 * Resolves the colour for a heart-rate zone.
 *
 * @param zone - Zone number, 1–5.
 * @returns The zone's colour (defaults to the top zone colour out of range).
 */
export function hrZoneColor(zone: number): string {
  return HR_ZONE_COLORS[zone - 1] ?? '#e24b4a'
}

/**
 * Extracts the decoded HR zone buckets from the HR stream, when present.
 *
 * @param streams - The activity's metric streams.
 * @returns The HR zone buckets, or `null` when no HR zones are available.
 */
export function extractHrZones(streams: ActivityStream[]): HrZoneBucket[] | null {
  const hrStream = streams.find((stream) => stream.streamType === STREAM_TYPE.hr)
  return hrStream?.hrZones ?? null
}
