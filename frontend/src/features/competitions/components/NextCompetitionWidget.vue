<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Calendar, Flag, MoonStar, Route, Trophy } from '@lucide/vue'

import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useNextCompetitionQuery } from '@/features/competitions/composables/useCompetitions'
import { formatMediumDate } from '@/utils/datetime'

/**
 * "Preparation" widget for the overview (Обзор) page: the user's next
 * upcoming competition with a training-readiness estimate — the server-side
 * mirror of the mobile client's local Preparation tab. Hidden entirely while
 * no race is coming up, exactly like the rest of the dashboard sections.
 */
const { t, locale } = useI18n()

const query = useNextCompetitionQuery()
const next = computed(() => query.data.value ?? null)
const race = computed(() => next.value?.competition ?? null)

/** Readiness fraction in [0, 1] for the progress bar (percent text = ×100). */
const readinessPct = computed(() => Math.round((next.value?.readiness ?? 0) * 100))

/** Race day as a localized medium date, or '' when unparseable. */
const raceDate = computed(() =>
  race.value ? formatMediumDate(race.value.competition_date, locale.value) : '',
)

const isLoading = computed(() => query.isPending.value)
const isHidden = computed(() => !isLoading.value && race.value === null)

/** Rest days before the race, mirroring the mobile Preparation tab. */
function restDays(distanceKm: number): number {
  if (distanceKm <= 5) return 2
  if (distanceKm <= 10) return 3
  if (distanceKm <= 21.5) return 7
  return 14
}

const taperStart = computed(() => {
  if (!race.value) return ''
  const [y, m, d] = race.value.competition_date.split('-').map(Number)
  if (!y || !m || !d) return ''
  const dt = new Date(y, m - 1, d)
  dt.setDate(dt.getDate() - restDays(race.value.distance_km))
  return formatMediumDate(
    `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`,
    locale.value,
  )
})

const gapKm = computed(() =>
  Math.max((next.value?.required_weekly_km ?? 0) - (next.value?.avg_weekly_km ?? 0), 0),
)

const statusKey = computed(() => {
  if (readinessPct.value >= 100) return 'statusReady'
  if (readinessPct.value >= 60) return 'statusBuilding'
  return 'statusBase'
})

const suggestionKey = computed(() => {
  if (readinessPct.value >= 100) return 'tipTaper'
  if ((next.value?.avg_weekly_km ?? 0) <= 0) return 'tipBase'
  return 'tipBuild'
})

/**
 * "in N day(s)" with correct plural forms — vue-i18n's built-in plural
 * syntax has no separate `few` bucket, so Russian picks its own key.
 */
function daysLeftText(daysLeft: number): string {
  if (daysLeft <= 0) return t('health.competition.raceToday')
  const lang = locale.value.split('-')[0] ?? 'en'
  if (lang === 'ru') {
    const m10 = daysLeft % 10
    const m100 = daysLeft % 100
    const key =
      m10 === 1 && m100 !== 11
        ? 'inDay'
        : m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)
          ? 'inDaysFew'
          : 'inDaysMany'
    return t(`health.competition.${key}`, { n: daysLeft })
  }
  const key = new Intl.PluralRules('en').select(daysLeft) === 'one' ? 'inDay' : 'inDays'
  return t(`health.competition.${key}`, { n: daysLeft })
}
</script>

<template>
  <div v-if="!isHidden">
    <p class="text-card-heading">{{ t('health.competition.sectionTitle') }}</p>
    <div v-if="isLoading" class="mt-2">
      <Skeleton class="h-44 w-full rounded-card" />
    </div>
    <Card v-else-if="race" class="mt-2 overflow-hidden p-0">
      <!-- Header band: race identity + countdown badge -->
      <div class="flex items-start justify-between gap-3 bg-primary/5 p-4">
        <div class="flex min-w-0 items-center gap-3">
          <span
            class="flex size-11 shrink-0 items-center justify-center rounded-full bg-primary/10"
          >
            <Trophy class="size-5 text-primary" />
          </span>
          <div class="min-w-0">
            <p class="truncate text-body font-semibold">{{ race.name }}</p>
            <p class="text-hint mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5">
              <span> <Calendar class="mr-1 inline size-3.5 -translate-y-px" />{{ raceDate }} </span>
              <span class="inline-flex items-center gap-1">
                <Route class="size-3.5" />{{ race.distance_km }} км
              </span>
            </p>
          </div>
        </div>
        <Badge variant="secondary" class="shrink-0">
          <Flag class="mr-1 size-3.5" />{{ daysLeftText(next?.days_left ?? 0) }}
        </Badge>
      </div>

      <div class="flex flex-col gap-3 p-4">
        <!-- Readiness -->
        <div class="flex items-end justify-between gap-3">
          <div>
            <p class="text-item-title leading-none">{{ readinessPct }}%</p>
            <p class="text-hint mt-1">
              {{ t('health.competition.readiness') }} · {{ t(`health.competition.${statusKey}`) }}
            </p>
          </div>
          <p v-if="race.note" class="text-hint max-w-55 truncate text-right">{{ race.note }}</p>
        </div>
        <div class="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            class="h-full rounded-full bg-primary transition-all"
            :style="{ width: `${readinessPct}%` }"
          />
        </div>

        <!-- Mini stats -->
        <div class="grid grid-cols-3 gap-2">
          <div class="rounded-input border px-2 py-1.5 text-center">
            <p class="text-body font-semibold">{{ next?.avg_weekly_km ?? 0 }}</p>
            <p class="text-hint">{{ t('health.competition.weekLabel') }}</p>
          </div>
          <div class="rounded-input border px-2 py-1.5 text-center">
            <p class="text-body font-semibold">{{ next?.required_weekly_km ?? 0 }}</p>
            <p class="text-hint">{{ t('health.competition.requiredLabel') }}</p>
          </div>
          <div class="rounded-input border px-2 py-1.5 text-center">
            <p class="text-body font-semibold">+{{ gapKm.toFixed(1) }}</p>
            <p class="text-hint">{{ t('health.competition.gapLabel') }}</p>
          </div>
        </div>

        <p class="text-hint">
          {{
            t('health.competition.volumeHint', {
              actual: next?.avg_weekly_km ?? 0,
              required: next?.required_weekly_km ?? 0,
            })
          }}
        </p>

        <!-- Taper + tip -->
        <div class="flex items-start gap-2 rounded-input bg-muted/60 px-3 py-2">
          <MoonStar class="mt-0.5 size-4 shrink-0 text-primary" />
          <p class="text-body">
            {{ t('health.competition.taperFrom', { date: taperStart }) }} ·
            {{ t(`health.competition.${suggestionKey}`) }}
          </p>
        </div>
      </div>
    </Card>
  </div>
</template>
