<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

interface Props {
  /** The value to display; the badge hides itself when the count is falsy (0 / nullish). */
  count?: number | null
  class?: HTMLAttributes['class']
}

const props = defineProps<Props>()
</script>

<template>
  <span
    v-if="count"
    data-slot="count-badge"
    :class="
      cn(
        'ml-1 inline-flex min-w-4 items-center justify-center rounded-full bg-primary px-1 text-xs font-medium text-primary-foreground',
        props.class,
      )
    "
  >
    {{ count }}
  </span>
</template>
