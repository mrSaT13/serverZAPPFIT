<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Copy, Download } from '@lucide/vue'

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
import { useToasts } from '@/composables/useToasts'
import { downloadBlob } from '@/lib/download'

const open = defineModel<boolean>('open', { required: true })

const props = defineProps<{
  /** The one-time backup codes to display. */
  codes: string[]
}>()

const { t } = useI18n()
const toasts = useToasts()

/** Copies all codes (newline-separated) to the clipboard. */
async function copyAll(): Promise<void> {
  try {
    await navigator.clipboard.writeText(props.codes.join('\n'))
    toasts.success(t('settings.security.backupCodes.copied'))
  } catch {
    toasts.error(t('settings.security.backupCodes.copyError'))
  }
}

/** Downloads the codes as a plain-text file. */
function download(): void {
  downloadBlob(
    new Blob([props.codes.join('\n')], { type: 'text/plain' }),
    'endurain-backup-codes.txt',
  )
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent :close-label="t('settings.security.close')">
      <DialogHeader>
        <DialogTitle>{{ t('settings.security.backupCodes.title') }}</DialogTitle>
        <DialogDescription>{{ t('settings.security.backupCodes.description') }}</DialogDescription>
      </DialogHeader>

      <Alert kind="warning" class="mt-4">
        {{ t('settings.security.backupCodes.warning') }}
      </Alert>

      <ul
        class="mt-4 grid grid-cols-2 gap-2 rounded-card border border-border p-3 font-mono text-sm"
      >
        <li v-for="codeValue in codes" :key="codeValue" class="select-all text-center">
          {{ codeValue }}
        </li>
      </ul>

      <DialogFooter class="mt-4">
        <Button variant="outline" @click="copyAll">
          <Copy class="size-4" aria-hidden="true" />
          {{ t('settings.security.backupCodes.copy') }}
        </Button>
        <Button variant="outline" @click="download">
          <Download class="size-4" aria-hidden="true" />
          {{ t('settings.security.backupCodes.download') }}
        </Button>
        <Button @click="open = false">{{ t('settings.security.backupCodes.done') }}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
