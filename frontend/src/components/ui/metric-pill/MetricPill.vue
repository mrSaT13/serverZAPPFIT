<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

import type { MetricPillVariants } from '.'
import { metricPillValueVariants } from '.'

interface Props {
  /** Short uppercase caption, e.g. "Distance". */
  label: string
  /** Formatted primary value, e.g. "12.4". */
  value: string | number
  /** Optional unit suffix shown next to the value, e.g. "km". */
  unit?: string
  /** Semantic colour for the value (defaults to neutral ink). */
  accent?: MetricPillVariants['accent']
  class?: HTMLAttributes['class']
}

const props = defineProps<Props>()
</script>

<template>
  <div data-slot="metric-pill" :class="cn('min-w-[100px] rounded-input', props.class)">
    <p class="mb-1 text-caption">
      {{ label }}
    </p>
    <p :class="metricPillValueVariants({ accent })">
      {{ value }}
      <span v-if="unit" class="text-hint font-normal">{{ unit }}</span>
    </p>
  </div>
</template>
