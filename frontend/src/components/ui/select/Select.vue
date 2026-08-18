<script setup lang="ts" generic="T extends string | number = string">
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'
import { inputFieldClass } from '@/components/ui/input/fieldClasses'

const props = defineProps<{ class?: HTMLAttributes['class'] }>()

/**
 * Two-way bound value for the select. Generic over the option value type so
 * callers binding a narrow string union (e.g. a gender or currency code) keep
 * full type-safety on both the model and the rendered `<option>` values.
 */
const model = defineModel<T>({ required: true })
</script>

<template>
  <select v-model="model" data-slot="select" :class="cn(inputFieldClass, props.class)">
    <slot />
  </select>
</template>
