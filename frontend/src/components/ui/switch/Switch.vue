<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

/**
 * Touch-friendly toggle switch backed by a native checkbox, so it works with
 * `v-model`, native form semantics, and keyboard out of the box. The checkbox
 * is visually hidden (`peer sr-only`) and exposed to assistive tech as a switch
 * via `role="switch"`; the track is a sibling whose `::after` pseudo-element is
 * the sliding thumb. The whole row (track + label) is a large tap target.
 */
const props = defineProps<{
  /** Disables interaction and dims the control. */
  disabled?: boolean
  /** Accessible label, required when no visible text is provided via the slot. */
  ariaLabel?: string
  /** Extra classes for the wrapping label. */
  class?: HTMLAttributes['class']
}>()

/** Two-way bound on/off state. */
const model = defineModel<boolean>({ required: true })
</script>

<template>
  <label
    :class="
      cn(
        'inline-flex items-center gap-3 py-1',
        disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer',
        props.class,
      )
    "
  >
    <input
      v-model="model"
      type="checkbox"
      role="switch"
      class="peer sr-only"
      :disabled="disabled"
      :aria-label="ariaLabel"
    />
    <span
      class="relative inline-flex h-6 w-11 shrink-0 rounded-full bg-muted-foreground/30 transition-colors after:absolute after:left-0.5 after:top-0.5 after:size-5 after:rounded-full after:bg-white after:shadow-sm after:transition-transform after:content-[''] peer-checked:bg-brand peer-checked:after:translate-x-5 peer-focus-visible:ring-3 peer-focus-visible:ring-ring/30 peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-card"
    />
    <span v-if="$slots.default" class="text-body">
      <slot />
    </span>
  </label>
</template>
