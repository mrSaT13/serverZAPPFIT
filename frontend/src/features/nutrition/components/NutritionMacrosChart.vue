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

const PROTEIN_COLOR = themeColor('--color-goal')
const CARBS_COLOR = themeColor('--color-info')
const FAT_COLOR = themeColor('--color-hr')

/** Short localized day label, e.g. «5 мая» / "5 May". */
function dayLabel(iso: string): string {
  const date = new Date(`${iso}T00:00:00`)
  return date.toLocaleDateString(locale.value, { day: 'numeric', month: 'short' })
}

const chartRender = computed<ChartRenderOptions>(() => ({
  kind: 'line',
  series: [
    {
      label: t('health.nutrition.trend.proteinSeries'),
      data: props.days.map((day) => Math.round(day.protein)),
      color: PROTEIN_COLOR,
    },
    {
      label: t('health.nutrition.trend.carbsSeries'),
      data: props.days.map((day) => Math.round(day.carbs)),
      color: CARBS_COLOR,
    },
    {
      label: t('health.nutrition.trend.fatSeries'),
      data: props.days.map((day) => Math.round(day.fat)),
      color: FAT_COLOR,
    },
  ],
  labels: props.days.map((day) => dayLabel(day.date)),
  valueFormat: (value) => `${Math.round(value)} ${t('health.nutrition.gramsShort')}`,
}))

useMetricChart(chartRender)
</script>

<template>
  <HealthChartCard :title="t('health.nutrition.trend.macros')" :accent-color="PROTEIN_COLOR">
    <!-- min-w-0 lets the canvas shrink inside the grid on mobile. -->
    <div ref="chartContainer" class="relative h-56 w-full min-w-0" />
  </HealthChartCard>
</template>
