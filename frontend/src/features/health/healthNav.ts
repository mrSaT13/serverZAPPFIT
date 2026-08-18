/**
 * Health sidebar zone config — the single source of truth for the health
 * sub-navigation, mirroring `settingsNav.ts`. Only the dashboard is built today;
 * the remaining zones surface as disabled "soon" items so the full health
 * roadmap is visible without dead links.
 */

import {
  Droplet,
  Footprints,
  HeartPulse,
  LayoutDashboard,
  Moon,
  Scale,
  Toilet,
  Utensils,
} from '@lucide/vue'
import type { LucideIcon } from '@lucide/vue'

/** A health sidebar zone (a sub-section of the health area). */
export interface HealthZone {
  /** The route name to navigate to. Empty for zones not yet built. */
  name: string
  /** i18n key for the zone's sidebar label. */
  labelKey: string
  /** The sidebar icon. */
  icon: LucideIcon
  /** Whether the zone has a built route yet; unbuilt zones render disabled. */
  implemented: boolean
}

/** The health sidebar zones, in display order. */
export const HEALTH_ZONES: readonly HealthZone[] = [
  {
    name: 'health-dashboard',
    labelKey: 'health.nav.dashboard',
    icon: LayoutDashboard,
    implemented: true,
  },
  { name: 'health-sleep', labelKey: 'health.nav.sleep', icon: Moon, implemented: true },
  { name: 'health-rhr', labelKey: 'health.nav.rhr', icon: HeartPulse, implemented: true },
  { name: 'health-steps', labelKey: 'health.nav.steps', icon: Footprints, implemented: true },
  { name: 'health-weight', labelKey: 'health.nav.weight', icon: Scale, implemented: true },
  { name: 'health-fasting', labelKey: 'health.nav.fasting', icon: Utensils, implemented: true },
  { name: 'health-water', labelKey: 'health.nav.water', icon: Droplet, implemented: true },
  { name: 'health-poop', labelKey: 'health.nav.poop', icon: Toilet, implemented: true },
]
