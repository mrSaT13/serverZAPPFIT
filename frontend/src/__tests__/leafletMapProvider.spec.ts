import { describe, expect, it } from 'vitest'

import { setMapProvider, useMapProvider } from '@/composables/useMapProvider'
import { boundsOf, createLeafletMapProvider, toLatLngs } from '@/providers/leafletMapProvider'

describe('toLatLngs', () => {
  it('converts geo points to [lat, lng] tuples preserving order', () => {
    expect(
      toLatLngs([
        { lat: 1, lng: 2 },
        { lat: 3, lng: 4 },
      ]),
    ).toEqual([
      [1, 2],
      [3, 4],
    ])
  })

  it('returns an empty array when there are no points', () => {
    expect(toLatLngs([])).toEqual([])
  })
})

describe('boundsOf', () => {
  it('returns null for an empty track', () => {
    expect(boundsOf({ points: [] })).toBeNull()
  })

  it('returns a degenerate box for a single point', () => {
    expect(boundsOf({ points: [{ lat: 10, lng: 20 }] })).toEqual([
      [10, 20],
      [10, 20],
    ])
  })

  it('spans the min/max latitude and longitude of all points', () => {
    expect(
      boundsOf({
        points: [
          { lat: 10, lng: -5 },
          { lat: -2, lng: 30 },
          { lat: 4, lng: 12 },
        ],
      }),
    ).toEqual([
      [-2, -5],
      [10, 30],
    ])
  })

  it('includes start and finish markers when computing bounds', () => {
    expect(
      boundsOf({
        points: [{ lat: 0, lng: 0 }],
        start: { lat: 50, lng: 60 },
        finish: { lat: -10, lng: -20 },
      }),
    ).toEqual([
      [-10, -20],
      [50, 60],
    ])
  })
})

describe('createLeafletMapProvider', () => {
  it('names the provider and registers as available behind the seam', () => {
    const provider = createLeafletMapProvider()
    expect(provider.name).toBe('leaflet')

    setMapProvider(provider)
    const { provider: active, isAvailable } = useMapProvider()
    expect(active.name).toBe('leaflet')
    expect(isAvailable).toBe(true)
  })
})
