<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { ChartRenderOptions } from '@/composables/useChartProvider'
import type { ExerciseProgress } from '@/features/strength/services/workouts'

import { Select } from '@/components/ui/select'
import { themeColor } from '@/lib/themeColor'
import HealthChartCard from '@/features/health/components/HealthChartCard.vue'
import { useMetricChart } from '@/composables/useMetricChart'

const props = defineProps<{
  /** Per-exercise progress (best-per-session points), newest points last. */
  progress: ExerciseProgress[]
}>()

const { t, locale } = useI18n()

const ONE_RM_COLOR = themeColor('--color-effort')
const WEIGHT_COLOR = themeColor('--color-brand-mid')

/** Exercises with at least one plottable point. */
const plottable = computed(() => props.progress.filter((p) => p.points.length > 0))

const selected = ref('')
// Keep a valid selection as the progress data loads or shrinks.
watch(
  plottable,
  (list) => {
    if (!list.some((p) => p.exercise_name === selected.value)) {
      selected.value = list[0]?.exercise_name ?? ''
    }
  },
  { immediate: true },
)

const active = computed(() => plottable.value.find((p) => p.exercise_name === selected.value))

/** Short localized point label, e.g. «12.05» / "12 May". */
function pointLabel(iso: string): string {
  const date = new Date(`${iso}T00:00:00`)
  return date.toLocaleDateString(locale.value, { day: 'numeric', month: 'short' })
}

const chartRender = computed<ChartRenderOptions>(() => {
  const points = active.value?.points ?? []
  const labels = points.map((point) => pointLabel(point.date))
  const kg = t('workouts.kg')
  return {
    kind: 'line',
    series: [
      {
        label: t('workouts.charts.oneRmSeries'),
        data: points.map((point) => Math.round((point.est_1rm ?? 0) * 10) / 10),
        color: ONE_RM_COLOR,
      },
      {
        label: t('workouts.charts.weightSeries'),
        data: points.map((point) => Math.round((point.best_weight_kg ?? 0) * 10) / 10),
        color: WEIGHT_COLOR,
        dashed: true,
      },
    ],
    labels,
    valueFormat: (value) => `${value.toFixed(1)} ${kg}`,
  }
})

useMetricChart(chartRender)
</script>

<template>
  <HealthChartCard :title="t('workouts.charts.oneRm')" :accent-color="ONE_RM_COLOR">
    <Select v-if="plottable.length > 1" v-model="selected" class="mb-2">
      <option v-for="p in plottable" :key="p.exercise_name" :value="p.exercise_name">
        {{ p.exercise_name }}
      </option>
    </Select>
    <!-- min-w-0 lets the canvas shrink inside the grid on mobile. -->
    <div ref="chartContainer" class="relative h-56 w-full min-w-0" />
  </HealthChartCard>
</template>
