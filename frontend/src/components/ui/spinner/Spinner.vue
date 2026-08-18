<script setup lang="ts">
import { LoaderCircle } from '@lucide/vue'
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

import { spinnerVariants, type SpinnerVariants } from '.'

interface Props {
  /** Glyph size. Defaults to `md`. */
  size?: SpinnerVariants['size']
  /**
   * Accessible label announced to assistive tech. When omitted the spinner is
   * purely decorative and hidden from the accessibility tree.
   */
  label?: string
  class?: HTMLAttributes['class']
}

const props = defineProps<Props>()
</script>

<template>
  <LoaderCircle
    data-slot="spinner"
    :class="cn(spinnerVariants({ size: props.size }), props.class)"
    :role="props.label ? 'status' : undefined"
    :aria-label="props.label"
    :aria-hidden="props.label ? undefined : true"
  />
</template>
