<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { computed } from 'vue'
import {
  DialogContent,
  type DialogContentEmits,
  type DialogContentProps,
  DialogPortal,
  useForwardPropsEmits,
} from 'reka-ui'
import { X } from '@lucide/vue'

import { cn } from '@/lib/utils'
import DialogOverlay from './DialogOverlay.vue'
import DialogClose from './DialogClose.vue'

const props = defineProps<
  DialogContentProps & {
    class?: HTMLAttributes['class']
    /** Hides the built-in close button (e.g. for required-action dialogs). */
    showClose?: boolean
    /** Accessible label for the built-in close button. */
    closeLabel?: string
  }
>()
const emits = defineEmits<DialogContentEmits>()

const delegatedProps = computed(() => {
  const { class: _class, showClose: _showClose, closeLabel: _closeLabel, ...delegated } = props
  return delegated
})

const forwarded = useForwardPropsEmits(delegatedProps, emits)
</script>

<template>
  <DialogPortal>
    <DialogOverlay />
    <DialogContent
      data-slot="dialog-content"
      v-bind="forwarded"
      :class="
        cn(
          'fixed top-1/2 left-1/2 z-50 grid w-full max-w-sm -translate-x-1/2 -translate-y-1/2 gap-3 rounded-card border border-border bg-card p-4 duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
          props.class,
        )
      "
    >
      <slot />

      <DialogClose
        v-if="showClose !== false"
        :aria-label="closeLabel"
        class="absolute end-3 top-3 inline-flex size-8 items-center justify-center rounded-input text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus:outline-none focus-visible:ring-3 focus-visible:ring-ring/30"
      >
        <X class="size-4" />
      </DialogClose>
    </DialogContent>
  </DialogPortal>
</template>
