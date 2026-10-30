<!-- Month calendar of strength sessions + competition flags.

Props take the already-loaded sessions and competitions; the grid groups
them by calendar day (local dates, Monday-first). Clicking a day selects it:
the panel below lists that day's sessions and races plus a "log session"
shortcut. Emits `log-session` so the parent opens its SessionDialog. -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { CalendarDays, ChevronLeft, ChevronRight, Flag, History, Trophy } from '@lucide/vue'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { Competition } from '@/features/competitions/services/competitions'
import type { WorkoutSession } from '@/features/strength/services/workouts'

const props = defineProps<{
  sessions: WorkoutSession[]
  competitions: Competition[]
  isLoading: boolean
}>()

const emit = defineEmits<{ 'log-session': [] }>()

const { t, locale } = useI18n()

const todayIso = (() => {
  const d = new Date()
  return isoDay(d.getFullYear(), d.getMonth(), d.getDate())
})()

/** First-of-month offset from today (0 = current month). */
const monthOffset = ref(0)
const selectedDay = ref<string>(todayIso)

function isoDay(y: number, m: number, d: number): string {
  return `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

const viewMonth = computed(() => {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth() + monthOffset.value, 1)
})

const monthTitle = computed(() =>
  new Intl.DateTimeFormat(locale.value, { month: 'long', year: 'numeric' }).format(viewMonth.value),
)

/** Short weekday names starting Monday, in the UI locale. */
const weekdayNames = computed(() => {
  // 2026-01-05 is a Monday — anchor the row on it.
  const monday = new Date(2026, 0, 5)
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday)
    d.setDate(monday.getDate() + i)
    return new Intl.DateTimeFormat(locale.value, { weekday: 'short' }).format(d)
  })
})

interface DayCell {
  key: string
  label: number | null
  iso: string | null
  isToday: boolean
  sessionCount: number
  setCount: number
  races: Competition[]
}

const weeks = computed<DayCell[][]>(() => {
  const first = viewMonth.value
  const year = first.getFullYear()
  const month = first.getMonth()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  // Monday-first leading blanks: JS Sunday=0..Saturday=6.
  const leading = (new Date(year, month, 1).getDay() + 6) % 7

  const sessionsByDay = new Map<string, WorkoutSession[]>()
  for (const s of props.sessions) {
    const day = (s.date ?? '').slice(0, 10)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) continue
    const list = sessionsByDay.get(day) ?? []
    list.push(s)
    sessionsByDay.set(day, list)
  }
  const racesByDay = new Map<string, Competition[]>()
  for (const c of props.competitions) {
    const day = (c.competition_date ?? '').slice(0, 10)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) continue
    const list = racesByDay.get(day) ?? []
    list.push(c)
    racesByDay.set(day, list)
  }

  const cells: DayCell[] = []
  for (let i = 0; i < leading; i++) {
    cells.push({ key: `blank-${i}`, label: null, iso: null, isToday: false, sessionCount: 0, setCount: 0, races: [] })
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const iso = isoDay(year, month, d)
    const daySessions = sessionsByDay.get(iso) ?? []
    cells.push({
      key: iso,
      label: d,
      iso,
      isToday: iso === todayIso,
      sessionCount: daySessions.length,
      setCount: daySessions.reduce((sum, s) => sum + (s.sets?.length ?? 0), 0),
      races: racesByDay.get(iso) ?? [],
    })
  }
  while (cells.length % 7 !== 0) {
    cells.push({ key: `trail-${cells.length}`, label: null, iso: null, isToday: false, sessionCount: 0, setCount: 0, races: [] })
  }
  const rows: DayCell[][] = []
  for (let i = 0; i < cells.length; i += 7) rows.push(cells.slice(i, i + 7))
  return rows
})

const selectedSessions = computed(() =>
  props.sessions.filter((s) => (s.date ?? '').slice(0, 10) === selectedDay.value),
)
const selectedRaces = computed(() =>
  props.competitions.filter((c) => (c.competition_date ?? '').slice(0, 10) === selectedDay.value),
)

const selectedTitle = computed(() => {
  const [y, m, d] = selectedDay.value.split('-').map(Number)
  if (!y || !m || !d) return selectedDay.value
  return new Intl.DateTimeFormat(locale.value, { day: 'numeric', month: 'long' }).format(
    new Date(y, m - 1, d),
  )
})

function prevMonth(): void {
  monthOffset.value -= 1
}
function nextMonth(): void {
  monthOffset.value += 1
}
function goToday(): void {
  monthOffset.value = 0
  selectedDay.value = todayIso
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <Card v-if="isLoading" class="flex flex-col gap-2 p-4">
      <Skeleton class="h-6 w-40" />
      <Skeleton class="h-56 w-full" />
    </Card>
    <template v-else>
      <Card class="flex min-w-0 flex-col gap-3 p-4">
        <div class="flex flex-wrap items-center gap-2">
          <CalendarDays class="size-5 shrink-0" />
          <h2 class="text-card-heading capitalize">{{ monthTitle }}</h2>
          <div class="ml-auto flex gap-1">
            <Button size="sm" variant="ghost" @click="prevMonth" :aria-label="t('workouts.calendar.prev')">
              <ChevronLeft class="size-4" />
            </Button>
            <Button size="sm" variant="ghost" @click="goToday">
              {{ t('workouts.calendar.today') }}
            </Button>
            <Button size="sm" variant="ghost" @click="nextMonth" :aria-label="t('workouts.calendar.next')">
              <ChevronRight class="size-4" />
            </Button>
          </div>
        </div>

        <div class="grid grid-cols-7 gap-1">
          <div v-for="name in weekdayNames" :key="name" class="text-hint py-1 text-center text-xs">
            {{ name }}
          </div>
          <template v-for="week in weeks" :key="week[0]?.key">
            <button
              v-for="cell in week"
              :key="cell.key"
              type="button"
              :disabled="cell.iso === null"
              @click="cell.iso && (selectedDay = cell.iso)"
              :class="[
                'flex min-h-12 flex-col items-center justify-start gap-0.5 rounded-input border p-1 sm:min-h-16',
                cell.iso === selectedDay
                  ? 'border-primary ring-1 ring-primary'
                  : 'border-transparent hover:border-border',
                cell.isToday && cell.iso !== selectedDay ? 'bg-primary/5' : '',
              ]"
            >
              <span
                v-if="cell.label !== null"
                :class="[
                  'text-xs font-medium sm:text-sm',
                  cell.isToday ? 'text-primary' : '',
                ]"
              >
                {{ cell.label }}
              </span>
              <span v-if="cell.sessionCount > 0" class="flex items-center gap-0.5">
                <span
                  v-for="n in Math.min(cell.sessionCount, 3)"
                  :key="n"
                  class="size-1.5 rounded-full bg-primary"
                  aria-hidden="true"
                />
              </span>
              <Trophy
                v-if="cell.races.length > 0"
                class="size-3.5 text-warning"
                aria-hidden="true"
              />
            </button>
          </template>
        </div>

        <div class="flex items-center gap-2 text-xs">
          <span class="flex items-center gap-1"><span class="size-1.5 rounded-full bg-primary" /> {{ t('workouts.calendar.legendSession') }}</span>
          <span class="flex items-center gap-1"><Trophy class="size-3.5 text-warning" /> {{ t('workouts.calendar.legendRace') }}</span>
        </div>
      </Card>

      <Card class="flex min-w-0 flex-col gap-2 p-4">
        <div class="flex flex-wrap items-center gap-2">
          <h3 class="text-card-heading">{{ selectedTitle }}</h3>
          <Button class="ml-auto" size="sm" variant="secondary" @click="emit('log-session')">
            <History class="size-4" /> {{ t('workouts.session.logEmpty') }}
          </Button>
        </div>
        <div v-if="selectedRaces.length > 0" class="flex flex-col gap-1">
          <div
            v-for="race in selectedRaces"
            :key="race.id"
            class="flex items-center gap-2 rounded-input border border-warning/30 bg-warning/5 px-3 py-2"
          >
            <Flag class="size-4 shrink-0 text-warning" />
            <span class="min-w-0 flex-1 truncate text-body font-medium">{{ race.name }}</span>
            <Badge variant="secondary" class="shrink-0">{{ race.distance_km }} км</Badge>
          </div>
        </div>
        <div v-if="selectedSessions.length > 0" class="flex flex-col gap-1">
          <div
            v-for="s in selectedSessions"
            :key="s.id"
            class="flex items-center gap-2 rounded-input border px-3 py-2"
          >
            <div class="flex min-w-0 flex-1 flex-col">
              <span class="text-body font-medium">
                {{ s.sets.length }} {{ t('workouts.setsShort') }}
                <template v-if="s.duration_min"> · {{ s.duration_min }} {{ t('workouts.minutesShort') }}</template>
              </span>
              <span v-if="s.comment" class="text-hint truncate">{{ s.comment }}</span>
            </div>
          </div>
        </div>
        <p v-if="selectedSessions.length === 0 && selectedRaces.length === 0" class="text-hint">
          {{ t('workouts.calendar.emptyDay') }}
        </p>
      </Card>
    </template>
  </div>
</template>
