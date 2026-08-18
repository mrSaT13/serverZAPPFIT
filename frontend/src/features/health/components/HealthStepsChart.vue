<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { ChartRenderOptions } from '@/composables/useChartProvider'
import type { StepsEntry } from '@/features/health/types'

import { themeColor } from '@/lib/themeColor'
import HealthChartCard from '@/features/health/components/HealthChartCard.vue'
import { useHealthMetricChart } from '@/features/health/composables/useHealthMetricChart'
import { formatHealthEntryDate, formatSteps } from '@/features/health/utils/healthFormat'

const props = defineProps<{
  /** The steps entries to plot (newest first, as returned by the backend). */
  entries: StepsEntry[]
  /** The user's daily steps target, drawn as a flat reference line. */
  targetSteps: number | null
}>()

const { t, locale } = useI18n()

const STEPS_COLOR = themeColor('--color-brand-mid')
const TARGET_COLOR = themeColor('--color-goal')

/**
 * Entries that carry a step count, oldest-first so the line reads left → right
 * in chronological order (the backend returns newest-first for the list).
 */
const plotted = computed(() =>
  props.entries
    .filter((entry) => entry.steps !== null)
    .slice()
    .reverse(),
)

/** Render options for the chart provider: a steps line plus an optional target line. */
const chartRender = computed<ChartRenderOptions>(() => {
  const labels = plotted.value.map((entry) => formatHealthEntryDate(entry.date, locale.value))
  const data = plotted.value.map((entry) => Math.round(entry.steps as number))
  const series: ChartRenderOptions['series'] = [
    { label: t('health.steps.chartStepsSeries'), data, color: STEPS_COLOR },
  ]
  if (props.targetSteps !== null && labels.length > 0) {
    const target = Math.round(props.targetSteps)
    series.push({
      label: t('health.steps.chartTargetSeries'),
      data: labels.map(() => target),
      color: TARGET_COLOR,
      dashed: true,
    })
  }
  return {
    kind: 'bar',
    series,
    labels,
    valueFormat: (value) => formatSteps(value),
  }
})

useHealthMetricChart(chartRender)
</script>

<template>
  <HealthChartCard :title="t('health.steps.chartTitle')" :accent-color="STEPS_COLOR">
    <!-- min-w-0 lets the canvas shrink inside the grid on mobile. -->
    <div ref="chartContainer" class="relative h-56 w-full min-w-0" />
  </HealthChartCard>
</template>
