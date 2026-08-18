<script setup lang="ts">
import { computed, type HTMLAttributes } from 'vue'

import { presentGearType } from '@/features/gears/utils/gearType'

const props = defineProps<{
  /** Numeric gear-type identifier (1–8). */
  type: number
  class?: HTMLAttributes['class']
}>()

const icon = computed(() => presentGearType(props.type).icon)
</script>

<template>
  <component :is="icon" :class="props.class" aria-hidden="true" />
</template>
