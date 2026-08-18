import {
  Bike,
  Droplets,
  Dumbbell,
  Footprints,
  type LucideIcon,
  MountainSnow,
  Sailboat,
  Snowflake,
  Wind,
} from '@lucide/vue'

/**
 * Numeric gear types, mirroring the backend gear-type identifiers (1–8). Kept
 * as a named constant so call sites read by name instead of magic numbers; the
 * wire contract is the integer, so these must stay in sync with the backend.
 */
export const GEAR_TYPE = {
  BICYCLE: 1,
  SHOES: 2,
  WETSUIT: 3,
  RACQUET: 4,
  SKIS: 5,
  SNOWBOARD: 6,
  WINDSURF: 7,
  WATER_SPORTS_BOARD: 8,
} as const

/** All selectable gear-type values, in display order. */
export const GEAR_TYPE_VALUES: readonly number[] = [
  GEAR_TYPE.BICYCLE,
  GEAR_TYPE.SHOES,
  GEAR_TYPE.WETSUIT,
  GEAR_TYPE.RACQUET,
  GEAR_TYPE.SKIS,
  GEAR_TYPE.SNOWBOARD,
  GEAR_TYPE.WINDSURF,
  GEAR_TYPE.WATER_SPORTS_BOARD,
]

/**
 * Everything a gear row/badge needs to render a type, derived purely from the
 * numeric gear type: a Lucide icon and an i18n label key. Keeping this a plain
 * data object means the mapping is unit-testable without mounting a component.
 *
 * @property icon - Lucide icon component representing the gear type.
 * @property labelKey - i18n key for the human-readable type name.
 */
export interface GearTypePresentation {
  icon: LucideIcon
  labelKey: string
}

const GEAR_TYPE_PRESENTATION: Record<number, GearTypePresentation> = {
  [GEAR_TYPE.BICYCLE]: { icon: Bike, labelKey: 'gears.types.bicycle' },
  [GEAR_TYPE.SHOES]: { icon: Footprints, labelKey: 'gears.types.shoes' },
  [GEAR_TYPE.WETSUIT]: { icon: Droplets, labelKey: 'gears.types.wetsuit' },
  [GEAR_TYPE.RACQUET]: { icon: Dumbbell, labelKey: 'gears.types.racquet' },
  [GEAR_TYPE.SKIS]: { icon: MountainSnow, labelKey: 'gears.types.skis' },
  [GEAR_TYPE.SNOWBOARD]: { icon: Snowflake, labelKey: 'gears.types.snowboard' },
  [GEAR_TYPE.WINDSURF]: { icon: Wind, labelKey: 'gears.types.windsurf' },
  [GEAR_TYPE.WATER_SPORTS_BOARD]: { icon: Sailboat, labelKey: 'gears.types.waterSportsBoard' },
}

/** Fallback so an unknown gear type never renders blank. */
const FALLBACK_PRESENTATION: GearTypePresentation = {
  icon: Dumbbell,
  labelKey: 'gears.types.unknown',
}

/**
 * Maps a numeric gear type to its icon and label key. Unknown types degrade to
 * a neutral fallback so a new backend type never renders blank.
 *
 * @param gearType - The numeric gear-type identifier (1–8).
 * @returns The icon component and i18n label key for the type.
 */
export function presentGearType(gearType: number): GearTypePresentation {
  return GEAR_TYPE_PRESENTATION[gearType] ?? FALLBACK_PRESENTATION
}
