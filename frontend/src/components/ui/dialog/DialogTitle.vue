<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { DialogTitle, type DialogTitleProps } from 'reka-ui'

import { cn } from '@/lib/utils'

const props = defineProps<DialogTitleProps & { class?: HTMLAttributes['class'] }>()
</script>

<template>
  <DialogTitle
    data-slot="dialog-title"
    :as="props.as"
    :as-child="props.asChild"
    :class="cn('text-section-heading', props.class)"
  >
    <slot />
  </DialogTitle>
</template>
