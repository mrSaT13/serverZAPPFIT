<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'
import { inputFieldClass } from './fieldClasses'

const props = defineProps<{ class?: HTMLAttributes['class'] }>()

/**
 * Two-way bound value for the input. Typed as string because every current
 * consumer binds a text-like field; numeric inputs should bind via a dedicated
 * number primitive rather than widening this type.
 */
const model = defineModel<string>({ default: '' })
</script>

<template>
  <input v-model="model" data-slot="input" :class="cn(inputFieldClass, props.class)" />
</template>
