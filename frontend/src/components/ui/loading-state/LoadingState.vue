<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

import { Spinner } from '../spinner'

interface Props {
  /**
   * Status message announced to assistive tech and shown beneath the spinner.
   * Falls back to a visually hidden default so the surface is always labelled.
   */
  label?: string
  /** Hides the textual label while keeping it available to screen readers. */
  hideLabel?: boolean
  class?: HTMLAttributes['class']
}

const props = defineProps<Props>()
</script>

<template>
  <div
    data-slot="loading-state"
    role="status"
    aria-live="polite"
    :class="
      cn('flex flex-col items-center justify-center gap-3 px-4 py-12 text-center', props.class)
    "
  >
    <Spinner size="lg" class="text-muted-foreground" />
    <p v-if="props.label" :class="cn('text-body', props.hideLabel && 'sr-only')">
      {{ props.label }}
    </p>
  </div>
</template>
