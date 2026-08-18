<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

import type { EmptyStateVariant } from '.'

interface Props {
  /** Primary message. */
  title: string
  /** Optional supporting copy (shown for the first-time variant). */
  description?: string
  /**
   * `first-time` is a rich state with icon + description + call-to-action for a
   * genuinely empty dataset; `filtered` is a quiet message for when filters
   * hide all rows.
   */
  variant?: EmptyStateVariant
  class?: HTMLAttributes['class']
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'first-time',
})
</script>

<template>
  <div
    v-if="props.variant === 'filtered'"
    data-slot="empty-state"
    data-variant="filtered"
    :class="cn('py-8 text-center text-body', props.class)"
  >
    {{ title }}
  </div>
  <div
    v-else
    data-slot="empty-state"
    data-variant="first-time"
    :class="cn('flex flex-col items-center gap-3 px-4 py-12 text-center', props.class)"
  >
    <div v-if="$slots.icon" class="text-muted-foreground">
      <slot name="icon" />
    </div>
    <p class="text-item-title">{{ title }}</p>
    <p v-if="description" class="max-w-sm text-body">{{ description }}</p>
    <div v-if="$slots.action" class="mt-1">
      <slot name="action" />
    </div>
  </div>
</template>
