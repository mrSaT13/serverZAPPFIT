import type { ActivityLap } from '@/features/activities/types'

import { activityTypeIsSwimming } from '@/features/activities/utils/activityType'

/** A lap enriched with swim-rest and relative-pace presentation data. */
export interface NormalizedLap {
  lap: ActivityLap
  /**
   * Whether this lap is a swim rest (zero/null distance). Two rests in a row are
   * treated as a drill rather than a rest, mirroring v1's heuristic.
   */
  swimIsRest: boolean
  /**
   * Pace relative to the fastest lap, clamped to 0–100 (100 = fastest). `null`
   * when the lap has no pace, so a progress bar can be omitted.
   */
  normalizedScore: number | null
}

/**
 * Enriches laps with swim-rest detection and a relative-pace score for the
 * mini progress bar. Pure (no formatting/i18n) so it is unit-testable; the
 * table component formats the underlying values.
 *
 * @param laps - The activity's laps, in order.
 * @param activityType - Numeric activity-type code (for swim detection).
 * @returns The laps enriched with rest/score data, in the same order.
 */
export function normalizeLaps(laps: ActivityLap[], activityType: number): NormalizedLap[] {
  if (laps.length === 0) {
    return []
  }

  const isSwimming = activityTypeIsSwimming(activityType)
  const paces = laps
    .map((lap) => lap.enhancedAvgPace)
    .filter((pace): pace is number => pace !== null && pace > 0)
  const fastestPace = paces.length > 0 ? Math.min(...paces) : null

  const entries: NormalizedLap[] = laps.map((lap) => ({
    lap,
    swimIsRest: isSwimming && (lap.totalDistance === null || lap.totalDistance === 0),
    normalizedScore: null,
  }))

  // Two rests in a row almost always means a drill set, not a real rest.
  for (let i = 0; i < entries.length - 1; i += 1) {
    const current = entries[i]
    const next = entries[i + 1]
    if (current && next && current.swimIsRest && next.swimIsRest) {
      next.swimIsRest = false
    }
  }

  for (const entry of entries) {
    const pace = entry.lap.enhancedAvgPace
    if (fastestPace !== null && pace !== null && pace > 0) {
      entry.normalizedScore = Math.min(Math.max((fastestPace / pace) * 100, 0), 100)
    }
  }

  return entries
}
