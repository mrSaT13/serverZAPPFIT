import { describe, expect, it } from 'vitest'

import type { ActivityStream, HrZoneBucket } from '@/features/activities/types'

import { extractHrZones, HR_ZONE_COLORS, hrZoneColor } from '@/features/activities/utils/hrZones'

/** Builds a stream fixture carrying optional HR zones. */
function stream(streamType: number, hrZones: HrZoneBucket[] | null = null): ActivityStream {
  return { id: streamType, streamType, waypoints: [], hrZones }
}

const ZONES: HrZoneBucket[] = [
  { zone: 1, percent: 25, hrRange: '< 100', timeSeconds: 900 },
  { zone: 2, percent: 30, hrRange: '100 - 129', timeSeconds: 1200 },
]

describe('extractHrZones', () => {
  it('returns the HR stream zones', () => {
    expect(extractHrZones([stream(4), stream(1, ZONES)])).toEqual(ZONES)
  })

  it('returns null when the HR stream lacks zones or is absent', () => {
    expect(extractHrZones([stream(1, null)])).toBeNull()
    expect(extractHrZones([stream(4)])).toBeNull()
  })
})

describe('hrZoneColor', () => {
  it('maps zones 1–5 to the colour ramp', () => {
    expect(hrZoneColor(1)).toBe(HR_ZONE_COLORS[0])
    expect(hrZoneColor(5)).toBe(HR_ZONE_COLORS[4])
  })

  it('falls back to the top-zone colour out of range', () => {
    expect(hrZoneColor(9)).toBe('#e24b4a')
  })
})
