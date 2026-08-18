import { describe, expect, it } from 'vitest'

import {
  ACTIVITY_CATEGORY_FILTERS,
  ALL_ACTIVITY_CATEGORIES,
  ALL_GEAR_TYPES,
  filterActivitiesByCategory,
  filterGearsByType,
} from '@/features/search/utils/filters'

/** Minimal activity shape the filter reads (one representative type per family). */
const activities = [
  { activityType: 1 }, // running
  { activityType: 4 }, // cycling
  { activityType: 8 }, // swimming
  { activityType: 11 }, // walking
  { activityType: 21 }, // racquet
  { activityType: 13 }, // rowing
  { activityType: 15 }, // snow skiing -> winterSports
  { activityType: 17 }, // snowboarding -> winterSports
  { activityType: 37 }, // ice skating -> winterSports
  { activityType: 30 }, // windsurf -> waterSports
  { activityType: 43 }, // sailing -> waterSports
  { activityType: 32 }, // stand-up paddling -> waterSports
  { activityType: 33 }, // surf -> waterSports
  { activityType: 45 }, // inline skating -> skating
]

describe('filterActivitiesByCategory', () => {
  it('returns a copy of every activity for the "all" sentinel', () => {
    const result = filterActivitiesByCategory(activities, ALL_ACTIVITY_CATEGORIES)

    expect(result).toHaveLength(activities.length)
    expect(result).not.toBe(activities)
  })

  it('returns every activity for an unknown category', () => {
    expect(filterActivitiesByCategory(activities, 'does-not-exist')).toHaveLength(activities.length)
  })

  it('keeps only single-family disciplines', () => {
    expect(filterActivitiesByCategory(activities, 'running')).toEqual([{ activityType: 1 }])
    expect(filterActivitiesByCategory(activities, 'cycling')).toEqual([{ activityType: 4 }])
    expect(filterActivitiesByCategory(activities, 'swimming')).toEqual([{ activityType: 8 }])
    expect(filterActivitiesByCategory(activities, 'racquet')).toEqual([{ activityType: 21 }])
    expect(filterActivitiesByCategory(activities, 'rowing')).toEqual([{ activityType: 13 }])
  })

  it('groups skiing, snowboarding, and ice skating under winter sports', () => {
    expect(filterActivitiesByCategory(activities, 'winterSports')).toEqual([
      { activityType: 15 },
      { activityType: 17 },
      { activityType: 37 },
    ])
  })

  it('groups windsurf, sailing, paddling, and surf under water sports', () => {
    expect(filterActivitiesByCategory(activities, 'waterSports')).toEqual([
      { activityType: 30 },
      { activityType: 43 },
      { activityType: 32 },
      { activityType: 33 },
    ])
  })

  it('keeps inline skating separate from ice skating', () => {
    expect(filterActivitiesByCategory(activities, 'skating')).toEqual([{ activityType: 45 }])
  })

  it('exposes a stable, duplicate-free set of category values', () => {
    const values = ACTIVITY_CATEGORY_FILTERS.map((filter) => filter.value)

    expect(new Set(values).size).toBe(values.length)
    expect(values.every((value) => value.length > 0)).toBe(true)
  })
})

describe('filterGearsByType', () => {
  const gears = [{ gearType: 1 }, { gearType: 2 }, { gearType: 2 }, { gearType: 5 }]

  it('returns a copy of every gear for the "all" sentinel', () => {
    const result = filterGearsByType(gears, ALL_GEAR_TYPES)

    expect(result).toHaveLength(gears.length)
    expect(result).not.toBe(gears)
  })

  it('keeps only gears of the requested type', () => {
    expect(filterGearsByType(gears, 2)).toEqual([{ gearType: 2 }, { gearType: 2 }])
    expect(filterGearsByType(gears, 5)).toEqual([{ gearType: 5 }])
  })

  it('returns nothing for a type with no matches', () => {
    expect(filterGearsByType(gears, 99)).toEqual([])
  })
})
