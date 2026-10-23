<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, BedDouble } from '@lucide/vue'

import type { SleepEntry } from '@/features/health/types'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { Skeleton } from '@/components/ui/skeleton'
import HealthSleepHypnogram from '@/features/health/components/HealthSleepHypnogram.vue'
import {
  useSleepByDateQuery,
  useSleepRangeStatsQuery,
} from '@/features/health/composables/useHealth'
import {
  formatHealthEntryDate,
  formatHoursMinutes,
  formatRestingHeartRate,
  formatSkinTempDeviation,
  hrvStatusKey,
  sleepScoreKey,
} from '@/features/health/utils/healthFormat'

const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()

/** The requested night (`YYYY-MM-DD`); empty when the route param is invalid. */
const nightDate = computed(() => {
  const raw = route.params.date
  const value = Array.isArray(raw) ? raw[0] : raw
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : ''
})

const nightQuery = useSleepByDateQuery(nightDate)
const night = computed(() => nightQuery.data.value ?? null)

/** The 7-night window ending on this night, for the average strip. */
const weekStart = computed(() => {
  if (!nightDate.value) return ''
  const day = new Date(`${nightDate.value}T12:00:00`)
  day.setDate(day.getDate() - 6)
  return day.toISOString().slice(0, 10)
})
const weekStatsQuery = useSleepRangeStatsQuery(weekStart, nightDate)
const weekStats = computed(() => weekStatsQuery.data.value ?? null)

const nightTitle = computed(() =>
  night.value?.date ? formatHealthEntryDate(night.value.date, locale.value) : nightDate.value,
)

/** Resolves a sleep score string to a localized label, or `null` when absent. */
function scoreText(score: string | null): string | null {
  if (score === null) return null
  const key = sleepScoreKey(score)
  return key ? t(`health.sleep.${key}`) : score
}

/** Stage-duration breakdown rows with share of the night's total sleep. */
const stageBreakdown = computed(() => {
  if (!night.value) return []
  const total = night.value.totalSleepSeconds ?? 0
  const rows = [
    { key: 'deep', seconds: night.value.deepSleepSeconds },
    { key: 'light', seconds: night.value.lightSleepSeconds },
    { key: 'rem', seconds: night.value.remSleepSeconds },
    { key: 'awake', seconds: night.value.awakeSleepSeconds },
  ]
  return rows
    .filter((row) => row.seconds !== null && row.seconds > 0)
    .map((row) => ({
      ...row,
      seconds: row.seconds as number,
      share: total > 0 ? ((row.seconds as number) / total) * 100 : 0,
    }))
})

const STAGE_COLORS: Record<string, string> = {
  deep: '#1e40af',
  light: '#2563eb',
  rem: '#60a5fa',
  awake: '#9ca3af',
}

/** Vitals rows (label + formatted value), skipping absent readings. */
const vitals = computed(() => {
  if (!night.value) return []
  const entry: SleepEntry = night.value
  const rows: { key: string; value: string }[] = []
  const push = (key: string, value: string | null) => {
    if (value !== null) rows.push({ key, value })
  }
  push(
    'health.sleep.detail.restingHeartRate',
    entry.restingHeartRate !== null ? formatRestingHeartRate(entry.restingHeartRate) : null,
  )
  if (entry.avgHeartRate !== null)
    push('health.sleep.detail.avgHeartRate', `${entry.avgHeartRate} ${t('activities.units.bpm')}`)
  if (entry.minHeartRate !== null)
    push('health.sleep.detail.minHeartRate', `${entry.minHeartRate} ${t('activities.units.bpm')}`)
  if (entry.maxHeartRate !== null)
    push('health.sleep.detail.maxHeartRate', `${entry.maxHeartRate} ${t('activities.units.bpm')}`)
  if (entry.avgSpo2 !== null) push('health.sleep.detail.spo2', `${entry.avgSpo2} %`)
  if (entry.lowestSpo2 !== null) push('health.sleep.detail.lowestSpo2', `${entry.lowestSpo2} %`)
  if (entry.highestSpo2 !== null) push('health.sleep.detail.highestSpo2', `${entry.highestSpo2} %`)
  if (entry.avgRespiration !== null) push('health.sleep.respirationAvg', `${entry.avgRespiration}`)
  if (entry.lowestRespiration !== null) push('health.sleep.respirationMin', `${entry.lowestRespiration}`)
  if (entry.highestRespiration !== null) push('health.sleep.respirationMax', `${entry.highestRespiration}`)
  if (entry.avgSleepStress !== null) push('health.sleep.detail.avgSleepStress', String(entry.avgSleepStress))
  if (entry.awakeCount !== null) push('health.sleep.detail.awakeCount', String(entry.awakeCount))
  push(
    'health.sleep.detail.skinTempDeviation',
    entry.avgSkinTempDeviation !== null
      ? formatSkinTempDeviation(entry.avgSkinTempDeviation)
      : null,
  )
  const hrvKey = entry.hrvStatus !== null ? hrvStatusKey(entry.hrvStatus) : null
  if (hrvKey) push('health.sleep.hrvLabel', t(`health.sleep.${hrvKey}`))
  return rows
})

const hasHypnogram = computed(() => (night.value?.sleepStages.length ?? 0) > 0)

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    void router.push({ name: 'health-sleep' })
  }
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <header class="flex flex-col gap-2">
      <Button variant="ghost" size="sm" class="self-start" @click="goBack">
        <ArrowLeft class="size-4" />
        {{ t('activities.back') }}
      </Button>
      <div class="flex min-w-0 flex-col gap-0.5">
        <h1 class="text-page-title flex items-center gap-2">
          <BedDouble class="size-5 shrink-0" aria-hidden="true" />
          <span class="truncate">{{ t('health.sleep.night.title') }}</span>
        </h1>
        <p v-if="nightTitle" class="text-body">{{ nightTitle }}</p>
      </div>
    </header>

    <div v-if="nightQuery.isPending.value" class="flex flex-col gap-3" aria-busy="true">
      <Card class="flex flex-col gap-3">
        <Skeleton class="h-6 w-40" />
        <Skeleton class="h-24 w-full" />
      </Card>
      <Card class="flex flex-col gap-3">
        <Skeleton class="h-6 w-56" />
        <Skeleton class="h-40 w-full" />
      </Card>
    </div>

    <EmptyState
      v-else-if="nightQuery.isError.value || !night"
      :title="t('health.sleep.night.noRecord')"
      :description="t('health.sleep.night.noRecordHint')"
      variant="first-time"
    />

    <template v-else>
      <!-- Score hero -->
      <Card class="flex flex-col gap-3">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h2 class="text-card-heading">{{ t('health.sleep.detail.score') }}</h2>
            <p v-if="night.totalSleepSeconds !== null" class="text-body">
              {{ formatHoursMinutes(night.totalSleepSeconds) }}
            </p>
          </div>
          <div
            v-if="night.sleepScoreOverall !== null"
            class="text-metric font-medium"
            aria-live="polite"
          >
            {{ night.sleepScoreOverall }}
          </div>
        </div>
        <div
          v-if="night.sleepScoreQuality !== null || night.sleepScoreDuration !== null"
          class="flex flex-wrap gap-2"
        >
          <span v-if="night.sleepScoreQuality !== null" class="text-hint">
            {{ t('health.sleep.detail.quality') }}: {{ scoreText(night.sleepScoreQuality) }}
          </span>
          <span v-if="night.sleepScoreDuration !== null" class="text-hint">
            {{ t('health.sleep.detail.duration') }}: {{ scoreText(night.sleepScoreDuration) }}
          </span>
        </div>
      </Card>

      <!-- Hypnogram -->
      <Card v-if="hasHypnogram" class="flex flex-col gap-3">
        <h2 class="text-card-heading">{{ t('health.sleep.night.hypnogram') }}</h2>
        <HealthSleepHypnogram :stages="night.sleepStages" />
      </Card>

      <!-- Stage breakdown -->
      <Card v-if="stageBreakdown.length > 0" class="flex flex-col gap-3">
        <h2 class="text-card-heading">{{ t('health.sleep.detail.breakdown') }}</h2>
        <div class="flex flex-col gap-2">
          <div v-for="row in stageBreakdown" :key="row.key" class="flex flex-col gap-1">
            <div class="flex items-baseline justify-between gap-2 text-body">
              <span>{{ t(`health.sleep.detail.${row.key}`) }}</span>
              <span class="text-hint">
                {{ formatHoursMinutes(row.seconds) }} · {{ row.share.toFixed(0) }}%
              </span>
            </div>
            <div class="h-2 overflow-hidden rounded-full bg-muted">
              <div
                class="h-full rounded-full"
                :style="{ width: `${Math.min(row.share, 100)}%`, backgroundColor: STAGE_COLORS[row.key] }"
              />
            </div>
          </div>
        </div>
      </Card>

      <!-- Vitals -->
      <Card v-if="vitals.length > 0" class="flex flex-col gap-3">
        <h2 class="text-card-heading">{{ t('health.sleep.night.vitals') }}</h2>
        <dl class="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">
          <div v-for="row in vitals" :key="row.key" class="flex flex-col gap-0.5">
            <dt class="text-hint">{{ t(row.key) }}</dt>
            <dd class="text-body font-medium">{{ row.value }}</dd>
          </div>
        </dl>
      </Card>

      <!-- 7-night average -->
      <Card class="flex flex-col gap-2">
        <h2 class="text-card-heading">{{ t('health.sleep.night.averageTitle') }}</h2>
        <Skeleton v-if="weekStatsQuery.isPending.value" class="h-5 w-3/4" />
        <p v-else-if="weekStats && weekStats.nights > 0" class="text-body">
          {{
            t('health.sleep.night.averageLine', {
              nights: weekStats.nights,
              duration:
                weekStats.avgTotalSleepSeconds !== null
                  ? formatHoursMinutes(Math.round(weekStats.avgTotalSleepSeconds))
                  : '–',
              score: weekStats.avgSleepScoreOverall !== null
                ? Math.round(weekStats.avgSleepScoreOverall)
                : '–',
            })
          }}
        </p>
        <p v-else class="text-hint">{{ t('health.sleep.night.noAverage') }}</p>
      </Card>
    </template>
  </div>
</template>
