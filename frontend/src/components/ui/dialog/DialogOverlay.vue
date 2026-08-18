<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { DialogOverlay, type DialogOverlayProps } from 'reka-ui'

import { cn } from '@/lib/utils'

const props = defineProps<DialogOverlayProps & { class?: HTMLAttributes['class'] }>()
</script>

<template>
  <DialogOverlay
    data-slot="dialog-overlay"
    :class="
      cn(
        'fixed inset-0 z-50 bg-black/40 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
        props.class,
      )
    "
  />
</template>
