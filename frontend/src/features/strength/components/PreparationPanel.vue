<!-- Preparation tab: race countdown, taper dates and readiness estimate.

Server-driven mirror of the mobile app's "Подготовка" tab: the readiness
progress (avg 28-day weekly km vs. what the race distance expects) is
computed by `GET /competitions/next`; rest days and tips mirror the mobile
rules so both ends agree. -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { CheckCircle2, Flag, Trophy } from '@lucide/vue'

import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { Skeleton } from '@/components/ui/skeleton'
import { useCompetitionsQuery, useNextCompetitionQuery } from '@/features/competitions/composables/useCompetitions'
import type { Competition } from '@/features/competitions/services/competitions'

const props = defineProps<{ isLoading: boolean }>()

const { t, locale } = useI18n()

const competitionsQuery = useCompetitionsQuery()
const nextQuery = useNextCompetitionQuery()

const competitions = computed(() => competitionsQuery.data.value ?? [])
const nextData = computed(() => nextQuery.data.value ?? null)

const selectedId = ref<number | null>(null)
watch(
  competitions,
  (list) => {
    // Default to the server's "next" race, else the soonest upcoming.
    const nextId = nextData.value?.competition?.id
    if (nextId && list.some((c) => c.id === nextId)) selectedId.value = nextId
    else if (selectedId.value === null && list.length > 0) {
      const soonest =
        list
          .filter((c) => c.status === 'upcoming')
          .sort((a, b) => a.competition_date.localeCompare(b.competition_date))[0] ?? list[0]
      selectedId.value = soonest?.id ?? null
    }
  },
  { immediate: true },
)

const selected = computed<Competition | null>(
  () => competitions.value.find((c) => c.id === selectedId.value) ?? null,
)

/** Parses `YYYY-MM-DD` (noUncheckedIndexedAccess-safe). */
function parseIsoDay(iso: string): Date {
  const p = iso.split('-').map(Number)
  const y = p[0] ?? 1970
  const m = (p[1] ?? 1) - 1
  const d = p[2] ?? 1
  return new Date(y, m, d)
}

const daysLeft = computed(() => {
  const c = selected.value
  if (!c) return 0
  const race = parseIsoDay(c.competition_date)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.round((race.getTime() - today.getTime()) / 86_400_000)
})

/** Rest days before the race — mirrors the mobile client's taper rule. */
const restDays = computed(() => {
  const km = selected.value?.distance_km ?? 0
  if (km <= 5) return 2
  if (km <= 10) return 3
  if (km <= 21.5) return 7
  return 14
})

const taperDate = computed(() => {
  const c = selected.value
  if (!c) return null
  const race = parseIsoDay(c.competition_date)
  return new Date(race.getFullYear(), race.getMonth(), race.getDate() - restDays.value)
})

/** Weekly km a race of this length expects — mirrors the mobile client. */
const requiredWeeklyKm = computed(() => {
  const km = selected.value?.distance_km ?? 0
  if (km <= 5) return 20
  if (km <= 10) return 30
  if (km <= 21.5) return 45
  return 60
})

/** Readiness only exists for the race the server picked as "next". */
const readiness = computed(() => {
  const c = selected.value
  if (!c || nextData.value?.competition?.id !== c.id) return null
  return nextData.value!.readiness
})

const avgWeeklyKm = computed(() => nextData.value?.avg_weekly_km ?? null)

const pct = computed(() => (readiness.value === null ? null : Math.round(readiness.value * 100)))

const taperTips = computed(() => {
  const c = selected.value
  if (!c) return []
  const control = Math.min(Math.max(c.distance_km / 3, 3), 12).toFixed(0)
  return [
    t('workouts.preparation.tipTaper'),
    t('workouts.preparation.tipControl', { km: control }),
    t('workouts.preparation.tipRest', { days: restDays.value }),
  ]
})

const baseTips = computed(() => [
  t('workouts.preparation.tipBase'),
  t('workouts.preparation.tipLong'),
  t('workouts.preparation.tipRecovery'),
])

const tips = computed(() => (pct.value !== null && pct.value >= 100 ? taperTips.value : baseTips.value))

function formatSecs(secs: number): string {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

const fmtDay = computed(
  () => (d: Date | null) =>
    d
      ? new Intl.DateTimeFormat(locale.value, { day: '2-digit', month: '2-digit', year: 'numeric' }).format(d)
      : '',
)
</script>

<template>
  <div class="flex flex-col gap-3">
    <Card v-if="props.isLoading || competitionsQuery.isPending.value" class="flex flex-col gap-2 p-4">
      <Skeleton class="h-6 w-48" />
      <Skeleton class="h-24 w-full" />
    </Card>
    <EmptyState
      v-else-if="competitions.length === 0"
      :title="t('workouts.preparation.empty.title')"
      :description="t('workouts.preparation.empty.description')"
    />
    <template v-else>
      <div v-if="competitions.length > 1" class="flex flex-wrap gap-2">
        <Button
          v-for="c in competitions"
          :key="c.id"
          size="sm"
          class="shrink-0"
          :variant="c.id === selectedId ? 'secondary' : 'ghost'"
          @click="selectedId = c.id"
        >
          <Flag v-if="c.status !== 'completed'" class="size-4" />
          <CheckCircle2 v-else class="size-4" />
          {{ c.name }}
        </Button>
      </div>

      <Card v-if="selected" class="flex min-w-0 flex-col gap-3 p-4">
        <div class="flex min-w-0 flex-wrap items-center gap-2">
          <Trophy class="size-5 shrink-0 text-warning" />
          <h2 class="text-card-heading min-w-0 truncate">{{ selected.name }}</h2>
          <Badge v-if="selected.status === 'completed'" variant="secondary" class="shrink-0">
            {{ t('workouts.preparation.finished') }}
          </Badge>
        </div>
        <p class="text-hint">
          {{ selected.distance_km.toFixed(1) }} {{ t('workouts.preparation.km') }} ·
          {{ fmtDay(new Date(selected.competition_date + 'T00:00:00')) }}
          <template v-if="selected.note"> · {{ selected.note }}</template>
        </p>

        <template v-if="selected.status !== 'completed'">
          <div class="grid grid-cols-2 gap-2">
            <div class="rounded-input border p-3 text-center">
              <div class="text-2xl font-bold">{{ Math.max(daysLeft, 0) }}</div>
              <div class="text-hint text-xs">{{ t('workouts.preparation.daysLeft') }}</div>
            </div>
            <div class="rounded-input border p-3 text-center">
              <div class="text-2xl font-bold">{{ restDays }}</div>
              <div class="text-hint text-xs">{{ t('workouts.preparation.restDays') }}</div>
            </div>
          </div>
          <p class="text-hint text-sm">
            {{ t('workouts.preparation.taperFrom', { date: fmtDay(taperDate) }) }}
          </p>
        </template>
        <div v-else class="flex flex-wrap gap-2 text-sm">
          <Badge v-if="selected.place" variant="secondary">
            {{ t('workouts.preparation.place', { place: selected.place }) }}
            <template v-if="selected.total_participants">
              / {{ selected.total_participants }}</template
            >
          </Badge>
          <Badge v-if="selected.result_time_s" variant="secondary">
            {{ t('workouts.preparation.result', { time: formatSecs(selected.result_time_s) }) }}
          </Badge>
        </div>

        <!-- Readiness (server estimate, only for the upcoming "next" race) -->
        <div v-if="pct !== null" class="flex flex-col gap-2 rounded-input border p-3">
          <div class="flex items-center gap-2 text-sm font-medium">
            <CheckCircle2 class="size-4 text-primary" />
            {{ t('workouts.preparation.readiness', { pct }) }}
          </div>
          <div class="bg-muted h-1.5 overflow-hidden rounded-full">
            <div class="bg-primary h-full rounded-full" :style="{ width: `${Math.min(pct, 100)}%` }" />
          </div>
          <p class="text-hint text-xs">
            {{ t('workouts.preparation.readinessDetails', { avg: (avgWeeklyKm ?? 0).toFixed(1), required: requiredWeeklyKm }) }}
          </p>
        </div>
        <p v-else-if="selected.status !== 'completed'" class="text-hint text-xs">
          {{ t('workouts.preparation.readinessNextOnly') }}
        </p>
      </Card>

      <Card v-if="selected && selected.status !== 'completed'" class="flex flex-col gap-1 p-4">
        <h3 class="text-card-heading">{{ t('workouts.preparation.tipsTitle') }}</h3>
        <div v-for="tip in tips" :key="tip" class="flex items-start gap-2 text-sm">
          <Flag class="text-muted-foreground mt-0.5 size-4 shrink-0" />
          <span>{{ tip }}</span>
        </div>
      </Card>
    </template>
  </div>
</template>
