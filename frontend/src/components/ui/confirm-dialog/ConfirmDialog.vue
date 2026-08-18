<script setup lang="ts">
import { LoaderCircle } from '@lucide/vue'

import type { ButtonVariants } from '@/components/ui/button'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

/**
 * Generic confirmation dialog for a single destructive (or otherwise
 * irreversible) action. Presentational and i18n-agnostic: every label is a
 * prop, so callers pass their own translated strings — the same convention as
 * `useForm`/validators. The caller holds the target entity and reacts to the
 * single `confirm` event.
 */
const open = defineModel<boolean>('open', { required: true })

withDefaults(
  defineProps<{
    /** Dialog heading. */
    title: string
    /** Body copy explaining the consequence (interpolate the entity name here). */
    description: string
    /** Label for the confirming action button. */
    confirmLabel: string
    /** Label for the dismiss button. */
    cancelLabel: string
    /** Accessible label for the built-in close (X) button. */
    closeLabel: string
    /** Whether the action is in flight; disables both buttons and shows a spinner. */
    pending?: boolean
    /** Button variant for the confirm action; defaults to `destructive`. */
    confirmVariant?: ButtonVariants['variant']
  }>(),
  { pending: false, confirmVariant: 'destructive' },
)

const emit = defineEmits<{
  /** The user confirmed the action. */
  confirm: []
}>()
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent :close-label="closeLabel">
      <DialogHeader>
        <DialogTitle>{{ title }}</DialogTitle>
        <DialogDescription>{{ description }}</DialogDescription>
      </DialogHeader>

      <DialogFooter class="mt-1">
        <Button type="button" variant="ghost" :disabled="pending" @click="open = false">
          {{ cancelLabel }}
        </Button>
        <Button
          type="button"
          :variant="confirmVariant"
          :disabled="pending"
          @click="emit('confirm')"
        >
          <LoaderCircle v-if="pending" class="size-4 animate-spin" aria-hidden="true" />
          <span>{{ confirmLabel }}</span>
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
