<script setup lang="ts">
/**
 * Nutrition trend charts: daily calories (intake bars + dashed burned line)
 * and the protein/carbs/fat lines. The date range is selectable (14/30/90
 * days); data comes from `GET /nutrition/trend` and refetches on change.
 */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChartLine } from '@lucide/vue'

import { Card } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { useToasts } from '@/composables/useToasts'
import NutritionCaloriesChart from '@/features/nutrition/components/NutritionCaloriesChart.vue'
import NutritionMacrosChart from '@/features/nutrition/components/NutritionMacrosChart.vue'
import { fetchTrend, type NutritionTrendPoint } from '@/features/nutrition/services/nutrition'

const { t } = useI18n()
const toasts = useToasts()

const RANGE_OPTIONS = [14, 30, 90] as const
// Native select values are strings — keep the ref string-typed.
const rangeDays = ref<'14' | '30' | '90'>('30')
const days = ref<NutritionTrendPoint[]>([])
const loading = ref(false)

/** ISO date of `daysBack` days ago, UTC-safe for `date` columns. */
function isoDaysAgo(daysBack: number): string {
  const d = new Date()
  d.setUTCDate(d.getUTCDate() - daysBack)
  return d.toISOString().slice(0, 10)
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const trend = await fetchTrend(isoDaysAgo(Number(rangeDays.value) - 1), isoDaysAgo(0))
    days.value = trend.days
  } catch (e: unknown) {
    toasts.error((e as Error)?.message || t('app.error.toast'))
  } finally {
    loading.value = false
  }
}

watch(rangeDays, load, { immediate: true })
</script>

<template>
  <Card class="flex flex-col gap-3">
    <div class="flex flex-wrap items-center gap-2">
      <ChartLine class="size-5" />
      <h2 class="text-card-heading">{{ t('health.nutrition.trend.title') }}</h2>
      <Select v-model="rangeDays" class="ml-auto w-auto">
        <option v-for="option in RANGE_OPTIONS" :key="option" :value="option">
          {{ t('health.nutrition.trend.rangeDays', { days: option }) }}
        </option>
      </Select>
    </div>

    <div v-if="loading" class="flex flex-col gap-2">
      <Skeleton class="h-56 w-full" />
      <Skeleton class="h-56 w-full" />
    </div>
    <div v-else-if="days.length === 0" class="text-hint py-6 text-center">
      {{ t('health.nutrition.trend.empty') }}
    </div>
    <div v-else class="grid gap-3 lg:grid-cols-2">
      <NutritionCaloriesChart :days="days" />
      <NutritionMacrosChart :days="days" />
    </div>
  </Card>
</template>
