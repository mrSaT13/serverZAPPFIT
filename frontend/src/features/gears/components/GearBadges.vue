<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Gear } from '@/features/gears/types'

import { Badge } from '@/components/ui/badge'

/**
 * Status and provenance badges for a gear: an inactive marker plus a "synced
 * from" badge for each integration that owns the gear (Strava / Garmin
 * Connect). Renders nothing — including its wrapper — when no badge applies, so
 * callers can drop it in next to a title without leaving empty space.
 */
const props = defineProps<{ gear: Gear }>()

const { t } = useI18n()

/** Whether at least one badge applies, gating the wrapper to avoid empty gaps. */
const hasBadges = computed(
  () =>
    !props.gear.active ||
    props.gear.stravaGearId !== null ||
    props.gear.garminConnectGearId !== null,
)
</script>

<template>
  <div v-if="hasBadges" class="flex flex-wrap items-center gap-2">
    <Badge v-if="!gear.active" variant="destructive">{{ t('gears.inactive') }}</Badge>
    <Badge v-if="gear.stravaGearId" variant="secondary">{{ t('gears.fromStrava') }}</Badge>
    <Badge v-if="gear.garminConnectGearId" variant="secondary">
      {{ t('gears.fromGarmin') }}
    </Badge>
  </div>
</template>
