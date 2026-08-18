import { describe, expect, it } from 'vitest'

import type { ActivityLap } from '@/features/activities/types'
import { normalizeLaps } from '@/features/activities/utils/laps'

function makeLap(overrides: Partial<ActivityLap> = {}): ActivityLap {
  return {
    id: 1,
    totalDistance: 1000,
    totalElapsedTime: 300,
    totalTimerTime: 300,
    enhancedAvgPace: 0.3,
    enhancedAvgSpeed: 3.3,
    totalAscent: 10,
    avgHeartRate: 150,
    avgCadence: 80,
    totalCycles: null,
    intensity: null,
    ...overrides,
  }
}

describe('normalizeLaps', () => {
  it('returns an empty array for no laps', () => {
    expect(normalizeLaps([], 1)).toEqual([])
  })

  it('scores each lap relative to the fastest pace (non-swimming)', () => {
    const result = normalizeLaps(
      [makeLap({ id: 1, enhancedAvgPace: 0.3 }), makeLap({ id: 2, enhancedAvgPace: 0.4 })],
      1,
    )
    expect(result.map((entry) => entry.swimIsRest)).toEqual([false, false])
    const scores = result.map((entry) => entry.normalizedScore)
    expect(scores[0]).toBe(100)
    expect(scores[1]).toBeCloseTo(75, 5)
  })

  it('returns a null score when a lap has no pace', () => {
    const result = normalizeLaps([makeLap({ id: 1, enhancedAvgPace: null })], 1)
    expect(result.map((entry) => entry.normalizedScore)).toEqual([null])
  })

  it('marks zero-distance swim laps as rests', () => {
    const result = normalizeLaps(
      [
        makeLap({ id: 1, totalDistance: 50, enhancedAvgPace: 0.5 }),
        makeLap({ id: 2, totalDistance: 0, enhancedAvgPace: null }),
        makeLap({ id: 3, totalDistance: 50, enhancedAvgPace: 0.6 }),
      ],
      8,
    )
    expect(result.map((entry) => entry.swimIsRest)).toEqual([false, true, false])
  })

  it('treats two consecutive swim rests as a drill (second is not a rest)', () => {
    const result = normalizeLaps(
      [
        makeLap({ id: 1, totalDistance: 0, enhancedAvgPace: null }),
        makeLap({ id: 2, totalDistance: 0, enhancedAvgPace: null }),
      ],
      8,
    )
    expect(result.map((entry) => entry.swimIsRest)).toEqual([true, false])
  })

  it('never flags rests for non-swimming activities', () => {
    const result = normalizeLaps([makeLap({ id: 1, totalDistance: 0, enhancedAvgPace: null })], 1)
    expect(result.map((entry) => entry.swimIsRest)).toEqual([false])
  })
})
