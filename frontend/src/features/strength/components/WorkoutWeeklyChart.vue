<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { ChartRenderOptions } from '@/composables/useChartProvider'
import type { WorkoutStatisticsPoint } from '@/features/strength/services/workouts'

import { themeColor } from '@/lib/themeColor'
import HealthChartCard from '@/features/health/components/HealthChartCard.vue'
import { useMetricChart } from '@/composables/useMetricChart'

const props = defineProps<{
  /** Monday-anchored weekly aggregates (oldest first, as returned by the API). */
  weeks: WorkoutStatisticsPoint[]
  /** Which weekly metric to plot. */
  metric: 'volume' | 'sessions'
}>()

const { t, locale } = useI18n()

const VOLUME_COLOR = themeColor('--color-brand')
const SESSIONS_COLOR = themeColor('--color-goal')

/** Short localized week label, e.g. «5 мая» / "5 May". */
function weekLabel(iso: string): string {
  const date = new Date(`${iso}T00:00:00`)
  return date.toLocaleDateString(locale.value, { day: 'numeric', month: 'short' })
}

const chartRender = computed<ChartRenderOptions>(() => {
  const labels = props.weeks.map((week) => weekLabel(week.week_start))
  const volume = props.metric === 'volume'
  const data = props.weeks.map((week) => (volume ? Math.round(week.volume_kg) : week.sessions))
  return {
    kind: 'bar',
    series: [
      {
        label: volume ? t('workouts.charts.volumeSeries') : t('workouts.charts.sessionsSeries'),
        data,
        color: volume ? VOLUME_COLOR : SESSIONS_COLOR,
      },
    ],
    labels,
    valueFormat: volume
      ? (value) => `${Math.round(value).toLocaleString(locale.value)} ${t('workouts.kg')}`
      : (value) => `${Math.round(value)}`,
  }
})

useMetricChart(chartRender)
</script>

<template>
  <HealthChartCard
    :title="metric === 'volume' ? t('workouts.charts.volume') : t('workouts.charts.sessions')"
    :accent-color="metric === 'volume' ? VOLUME_COLOR : SESSIONS_COLOR"
  >
    <!-- min-w-0 lets the canvas shrink inside the grid on mobile. -->
    <div ref="chartContainer" class="relative h-56 w-full min-w-0" />
  </HealthChartCard>
</template>
