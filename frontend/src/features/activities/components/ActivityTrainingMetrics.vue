<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { Activity } from '@/features/activities/types'

import { Card } from '@/components/ui/card'

const props = defineProps<{
  activity: Activity
}>()

const { t } = useI18n()

function has(value: number | null | undefined): value is number {
  return value !== null && value !== undefined && Number.isFinite(value)
}

interface Metric {
  key: string
  labelKey: string
  value: string
  unit: string
  color: string
}

const metrics = computed<Metric[]>(() => {
  const a = props.activity
  const items: Metric[] = []

  if (has(a.vo2max)) {
    items.push({
      key: 'vo2max',
      labelKey: 'activities.training.vo2max',
      value: a.vo2max.toFixed(1),
      unit: 'ml/kg/min',
      color: 'text-blue-500',
    })
  }
  if (has(a.tss)) {
    items.push({
      key: 'tss',
      labelKey: 'activities.training.tss',
      value: String(a.tss),
      unit: '',
      color: 'text-orange-500',
    })
  }
  if (has(a.hrTss)) {
    items.push({
      key: 'hrTss',
      labelKey: 'activities.training.hrTss',
      value: String(a.hrTss),
      unit: '',
      color: 'text-orange-400',
    })
  }
  if (has(a.trimp)) {
    items.push({
      key: 'trimp',
      labelKey: 'activities.training.trimp',
      value: String(a.trimp),
      unit: '',
      color: 'text-red-400',
    })
  }
  if (has(a.intensityFactor)) {
    items.push({
      key: 'if',
      labelKey: 'activities.training.intensityFactor',
      value: a.intensityFactor.toFixed(2),
      unit: '',
      color: 'text-purple-500',
    })
  }
  if (has(a.aerobicTe)) {
    items.push({
      key: 'aerobicTe',
      labelKey: 'activities.training.aerobicTe',
      value: a.aerobicTe.toFixed(1),
      unit: '/5.0',
      color: 'text-green-500',
    })
  }
  if (has(a.anaerobicTe)) {
    items.push({
      key: 'anaerobicTe',
      labelKey: 'activities.training.anaerobicTe',
      value: a.anaerobicTe.toFixed(1),
      unit: '/5.0',
      color: 'text-red-500',
    })
  }
  if (has(a.epoc)) {
    items.push({
      key: 'epoc',
      labelKey: 'activities.training.epoc',
      value: a.epoc.toFixed(0),
      unit: 'kcal',
      color: 'text-yellow-500',
    })
  }
  if (has(a.sufferScore)) {
    items.push({
      key: 'sufferScore',
      labelKey: 'activities.training.sufferScore',
      value: String(a.sufferScore),
      unit: '/100',
      color: 'text-rose-500',
    })
  }
  if (has(a.efficiencyFactor)) {
    items.push({
      key: 'ef',
      labelKey: 'activities.training.efficiencyFactor',
      value: a.efficiencyFactor.toFixed(2),
      unit: '',
      color: 'text-teal-500',
    })
  }

  return items
})
</script>

<template>
  <Card v-if="metrics.length > 0" class="flex flex-col gap-3">
    <div class="flex items-center gap-2">
      <span class="size-2.5 rounded-full bg-brand" aria-hidden="true" />
      <h3 class="text-card-heading">{{ t('activities.training.title') }}</h3>
    </div>
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      <div v-for="m in metrics" :key="m.key" class="flex flex-col gap-0.5">
        <p class="text-caption">{{ t(m.labelKey) }}</p>
        <p class="text-item-title font-semibold tabular-nums" :class="m.color">
          {{ m.value }}<span v-if="m.unit" class="ml-0.5 text-caption">{{ m.unit }}</span>
        </p>
      </div>
    </div>
  </Card>
</template>
