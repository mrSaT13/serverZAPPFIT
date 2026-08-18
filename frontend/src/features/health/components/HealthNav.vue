<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { Check, ChevronDown, Menu } from '@lucide/vue'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { HEALTH_ZONES } from '@/features/health/healthNav'

/**
 * Health sidebar. Lists the health zones and highlights the active one, driven
 * by the shared {@link HEALTH_ZONES} config so it stays in sync with the route
 * table. Zones without a built route render as disabled "soon" items. Below
 * `lg` the rail collapses to a menu button (mirroring the settings sidebar).
 */
const { t } = useI18n()
const route = useRoute()
const router = useRouter()

/** Active styling applied to the zone that owns the current route. */
const ACTIVE_CLASS =
  'bg-brand-light font-medium text-brand-mid hover:bg-brand-light hover:text-brand-mid dark:bg-brand-dark-surface dark:text-brand-dark-foreground dark:hover:bg-brand-dark-surface dark:hover:text-brand-dark-foreground'

/**
 * Whether a zone owns the current route. Matches the zone's base path and any
 * nested route beneath it.
 *
 * @param zoneName - The zone's route name (empty for unbuilt zones).
 * @returns Whether the zone is the active one.
 */
function isZoneActive(zoneName: string): boolean {
  if (!zoneName) return false
  const base = router.resolve({ name: zoneName }).path
  return route.path === base || route.path.startsWith(`${base}/`)
}

/** The zone owning the current route, shown in the mobile menu trigger. */
const activeZone = computed(
  () => HEALTH_ZONES.find((zone) => zone.implemented && isZoneActive(zone.name)) ?? null,
)
</script>

<template>
  <div>
    <!-- Below lg: a menu button (opens the zone list) instead of a tall stacked list. -->
    <div class="lg:hidden">
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button variant="outline" class="w-full justify-between">
            <span class="flex min-w-0 items-center gap-2">
              <component
                :is="activeZone?.icon ?? Menu"
                class="size-4 shrink-0"
                aria-hidden="true"
              />
              <span class="truncate">
                {{ activeZone ? t(activeZone.labelKey) : t('health.nav.label') }}
              </span>
            </span>
            <ChevronDown class="size-4 shrink-0 opacity-60" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" class="w-56">
          <template v-for="zone in HEALTH_ZONES" :key="zone.labelKey">
            <DropdownMenuItem v-if="zone.implemented" as-child>
              <RouterLink
                :to="{ name: zone.name }"
                :aria-current="isZoneActive(zone.name) ? 'page' : undefined"
              >
                <component :is="zone.icon" class="size-4 shrink-0" aria-hidden="true" />
                <span class="truncate">{{ t(zone.labelKey) }}</span>
                <Check
                  v-if="isZoneActive(zone.name)"
                  class="ml-auto size-4 shrink-0"
                  aria-hidden="true"
                />
              </RouterLink>
            </DropdownMenuItem>
            <DropdownMenuItem v-else disabled>
              <component :is="zone.icon" class="size-4 shrink-0" aria-hidden="true" />
              <span class="truncate">{{ t(zone.labelKey) }}</span>
              <Badge variant="secondary" class="ml-auto">{{ t('health.nav.soon') }}</Badge>
            </DropdownMenuItem>
          </template>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>

    <!-- lg and up: the full sidebar rail. -->
    <Card padding="none" class="hidden lg:block">
      <nav class="flex flex-col gap-1 p-3" :aria-label="t('health.nav.label')">
        <template v-for="zone in HEALTH_ZONES" :key="zone.labelKey">
          <RouterLink
            v-if="zone.implemented"
            :to="{ name: zone.name }"
            class="flex items-center gap-3 rounded-input px-3 py-2 text-body transition-colors hover:bg-accent hover:text-accent-foreground"
            :class="isZoneActive(zone.name) ? ACTIVE_CLASS : ''"
            :aria-current="isZoneActive(zone.name) ? 'page' : undefined"
          >
            <component :is="zone.icon" class="size-4 shrink-0" aria-hidden="true" />
            {{ t(zone.labelKey) }}
          </RouterLink>
          <div
            v-else
            class="flex items-center gap-3 rounded-input px-3 py-2 text-body opacity-60"
            aria-disabled="true"
          >
            <component :is="zone.icon" class="size-4 shrink-0" aria-hidden="true" />
            <span>{{ t(zone.labelKey) }}</span>
            <Badge variant="secondary" class="ml-auto">{{ t('health.nav.soon') }}</Badge>
          </div>
        </template>
      </nav>
    </Card>
  </div>
</template>
