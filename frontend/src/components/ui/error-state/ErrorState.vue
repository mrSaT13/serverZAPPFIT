<script setup lang="ts">
import { TriangleAlert } from '@lucide/vue'
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

interface Props {
  /** Primary error headline. */
  title: string
  /** Optional supporting copy explaining the failure or next step. */
  description?: string
  class?: HTMLAttributes['class']
}

const props = defineProps<Props>()

const emit = defineEmits<{
  /** Emitted when the built-in retry affordance is activated. */
  retry: []
}>()
</script>

<template>
  <div
    data-slot="error-state"
    role="alert"
    :class="cn('flex flex-col items-center gap-3 px-4 py-12 text-center', props.class)"
  >
    <div class="text-destructive">
      <slot name="icon">
        <TriangleAlert class="size-8" aria-hidden="true" />
      </slot>
    </div>
    <p class="text-item-title">{{ title }}</p>
    <p v-if="description" class="max-w-sm text-body">
      {{ description }}
    </p>
    <div v-if="$slots.action" class="mt-1">
      <slot name="action" :retry="() => emit('retry')" />
    </div>
  </div>
</template>
