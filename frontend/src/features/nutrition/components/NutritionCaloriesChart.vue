<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { ChartRenderOptions } from '@/composables/useChartProvider'
import type { NutritionTrendPoint } from '@/features/nutrition/services/nutrition'

import { themeColor } from '@/lib/themeColor'
import HealthChartCard from '@/features/health/components/HealthChartCard.vue'
import { useMetricChart } from '@/composables/useMetricChart'

const props = defineProps<{
  /** Per-day totals, oldest first (as returned by `GET /nutrition/trend`). */
  days: NutritionTrendPoint[]
}>()

const { t, locale } = useI18n()

const CALORIES_COLOR = themeColor('--color-brand')
const BURNED_COLOR = themeColor('--color-effort')

/** Short localized day label, e.g. «5 мая» / "5 May". */
function dayLabel(iso: string): string {
  const date = new Date(`${iso}T00:00:00`)
  return date.toLocaleDateString(locale.value, { day: 'numeric', month: 'short' })
}

const chartRender = computed<ChartRenderOptions>(() => ({
  kind: 'bar',
  series: [
    {
      label: t('health.nutrition.trend.caloriesSeries'),
      data: props.days.map((day) => Math.round(day.calories)),
      color: CALORIES_COLOR,
    },
    {
      label: t('health.nutrition.trend.burnedSeries'),
      data: props.days.map((day) => Math.round(day.burned_calories ?? 0)),
      color: BURNED_COLOR,
      dashed: true,
    },
  ],
  labels: props.days.map((day) => dayLabel(day.date)),
  valueFormat: (value) =>
    `${Math.round(value).toLocaleString(locale.value)} ${t('health.nutrition.kcal')}`,
}))

useMetricChart(chartRender)
</script>

<template>
  <HealthChartCard :title="t('health.nutrition.trend.calories')" :accent-color="CALORIES_COLOR">
    <!-- min-w-0 lets the canvas shrink inside the grid on mobile. -->
    <div ref="chartContainer" class="relative h-56 w-full min-w-0" />
  </HealthChartCard>
</template>
