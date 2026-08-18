<script setup lang="ts">
import type { HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

interface Props {
  class?: HTMLAttributes['class']
}

const props = defineProps<Props>()
</script>

<template>
  <div
    data-slot="skeleton"
    aria-hidden="true"
    :class="cn('animate-pulse rounded-input bg-muted-foreground/20', props.class)"
  />
</template>
