import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Activity, Bike, Calendar, Heart, List, Search, type LucideIcon } from '@lucide/vue'

import { useAuthStore } from '@/features/auth/stores/auth'

/**
 * A single primary navigation entry, shared between the desktop top bar and
 * the mobile bottom navigation so both stay in sync from one source.
 *
 * @property name - Target route name.
 * @property label - Translated, user-facing label.
 * @property icon - Lucide icon component.
 * @property children - Optional sub-destinations; when present the entry
 *   renders as a dropdown instead of a direct link.
 */
export interface NavLink {
  name: string
  label: string
  icon: LucideIcon
  children?: NavLink[]
}

/**
 * Provides the app's primary navigation links. Centralised here so the
 * desktop navbar and the mobile bottom nav render identical destinations.
 *
 * @returns The reactive `primaryLinks`, shown only to authenticated users.
 */
export function useNavigation() {
  const { t } = useI18n()
  const auth = useAuthStore()

  const primaryLinks = computed<NavLink[]>(() =>
    auth.isAuthenticated
      ? [
          {
            name: 'activities',
            label: t('nav.activities'),
            icon: Activity,
            children: [
              { name: 'activities', label: t('nav.activitiesList'), icon: List },
              { name: 'summary', label: t('nav.summary'), icon: Calendar },
            ],
          },
          { name: 'gears', label: t('nav.gear'), icon: Bike },
          { name: 'health', label: t('nav.health'), icon: Heart },
          { name: 'search', label: t('nav.search'), icon: Search },
        ]
      : [],
  )

  return { primaryLinks }
}
