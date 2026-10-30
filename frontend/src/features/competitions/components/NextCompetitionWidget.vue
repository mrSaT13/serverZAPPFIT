<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Calendar, Trophy } from '@lucide/vue'

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
  <div>
    <p class="text-card-heading">{{ t('health.competition.sectionTitle') }}</p>
    <div v-if="isLoading" class="mt-2">
      <Skeleton class="h-28 w-full" />
    </div>
    <Card v-else-if="!isHidden && race" class="mt-2">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <Trophy class="size-4 shrink-0 opacity-60" />
            <p class="truncate text-body font-medium">{{ race.name }}</p>
          </div>
          <p class="text-hint mt-1">
            <Calendar class="mr-1 inline size-3.5 -translate-y-px" />
            {{ raceDate }} · {{ daysLeftText(next?.days_left ?? 0) }}
          </p>
          <p v-if="race.note" class="text-hint mt-1 line-clamp-1">{{ race.note }}</p>
        </div>
        <div class="shrink-0 text-right">
          <p class="text-card-heading">{{ readinessPct }}%</p>
          <p class="text-hint">{{ t('health.competition.readiness') }}</p>
        </div>
      </div>

      <div class="mt-3">
        <div class="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            class="h-full rounded-full bg-primary transition-all"
            :style="{ width: `${readinessPct}%` }"
          />
        </div>
        <p class="text-hint mt-1">
          {{
            t('health.competition.volumeHint', {
              actual: next?.avg_weekly_km ?? 0,
              required: next?.required_weekly_km ?? 0,
            })
          }}
        </p>
      </div>
    </Card>
  </div>
</template>
