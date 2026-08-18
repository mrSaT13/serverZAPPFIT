<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Copy } from '@lucide/vue'

import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import { useToasts } from '@/composables/useToasts'

const open = defineModel<boolean>('open', { required: true })

const props = defineProps<{
  /** The one-time raw API key to display. Never recoverable after this. */
  apiKey: string
}>()

const { t } = useI18n()
const toasts = useToasts()

// The user must acknowledge they've saved the key before the dialog will close
// via the primary button — the key cannot be shown again.
const acknowledged = ref(false)

watch(open, (isOpen) => {
  if (isOpen) {
    acknowledged.value = false
  }
})

/** Copies the raw key to the clipboard. */
async function copyKey(): Promise<void> {
  try {
    await navigator.clipboard.writeText(props.apiKey)
    toasts.success(t('settings.security.apiKeys.copied'))
  } catch {
    toasts.error(t('settings.security.apiKeys.copyError'))
  }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent :close-label="t('settings.security.close')">
      <DialogHeader>
        <DialogTitle>{{ t('settings.security.apiKeys.revealTitle') }}</DialogTitle>
        <DialogDescription>
          {{ t('settings.security.apiKeys.revealDescription') }}
        </DialogDescription>
      </DialogHeader>

      <Alert kind="warning" class="mt-4">
        {{ t('settings.security.apiKeys.revealWarning') }}
      </Alert>

      <div
        class="mt-4 select-all break-all rounded-card border border-border bg-muted-foreground/10 p-3 font-mono text-sm"
      >
        {{ apiKey }}
      </div>

      <div class="mt-4">
        <Button variant="outline" @click="copyKey">
          <Copy class="size-4" aria-hidden="true" />
          {{ t('settings.security.apiKeys.copy') }}
        </Button>
      </div>

      <Switch v-model="acknowledged" class="mt-4">
        {{ t('settings.security.apiKeys.revealConfirm') }}
      </Switch>

      <DialogFooter class="mt-4">
        <Button :disabled="!acknowledged" @click="open = false">
          {{ t('settings.security.apiKeys.revealDone') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
