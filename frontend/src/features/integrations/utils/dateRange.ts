import type { DateRange } from '@/features/integrations/types'

/** Formats a `Date` as a `YYYY-MM-DD` string (UTC, matching the v1 behaviour). */
function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10)
}

/**
 * Builds an inclusive date window spanning the last `days` days up to today,
 * mirroring the v1 "retrieve last N days" option.
 *
 * @param days - Number of days back from today the window should start.
 * @returns The `{ startDate, endDate }` window as `YYYY-MM-DD` strings.
 */
export function daysAgoRange(days: number): DateRange {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - days)
  return { startDate: toIsoDate(start), endDate: toIsoDate(end) }
}
