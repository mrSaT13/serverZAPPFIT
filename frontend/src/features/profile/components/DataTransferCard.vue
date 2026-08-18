<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Download, LoaderCircle, Upload } from '@lucide/vue'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useToasts } from '@/composables/useToasts'
import { downloadBlob } from '@/lib/download'
import {
  useExportProfileMutation,
  useImportProfileMutation,
} from '@/features/profile/composables/useDataTransfer'

const props = defineProps<{
  /** The current user's id, used to name the export archive. */
  userId: number
}>()

const { t } = useI18n()
const toasts = useToasts()
const exportMutation = useExportProfileMutation()
const importMutation = useImportProfileMutation()

const fileInput = ref<HTMLInputElement | null>(null)

/** Exports the user's data and saves the returned archive to disk. */
function handleExport(): void {
  exportMutation.mutate(undefined, {
    onSuccess: (blob) => {
      const stamp = new Date().toISOString().slice(0, 16).replace(':', '-')
      downloadBlob(blob, `endurain_user_${props.userId}_${stamp}.zip`)
      toasts.success(t('settings.profile.dataTransfer.exportSuccess'))
    },
    onError: () => toasts.error(t('settings.profile.dataTransfer.exportError')),
  })
}

/** Opens the native file picker for the import archive. */
function pickArchive(): void {
  fileInput.value?.click()
}

/**
 * Validates the chosen file is a ZIP archive and imports it. The input is
 * always reset so re-selecting the same file fires `change` again.
 *
 * @param event - The file input change event.
 */
function onArchiveChange(event: Event): void {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) {
    return
  }
  const isZip =
    file.type === 'application/zip' ||
    file.type === 'application/x-zip-compressed' ||
    file.name.toLowerCase().endsWith('.zip')
  if (!isZip) {
    toasts.error(t('settings.profile.dataTransfer.invalidType'))
    return
  }
  importMutation.mutate(file, {
    onSuccess: () => toasts.success(t('settings.profile.dataTransfer.importSuccess')),
    onError: () => toasts.error(t('settings.profile.dataTransfer.importError')),
  })
}
</script>

<template>
  <Card class="flex flex-col gap-3">
    <div class="flex flex-col gap-1">
      <h2 class="text-card-heading">{{ t('settings.profile.dataTransfer.title') }}</h2>
      <p class="text-body">{{ t('settings.profile.dataTransfer.subtitle') }}</p>
    </div>

    <input
      ref="fileInput"
      type="file"
      accept=".zip,application/zip"
      class="sr-only"
      @change="onArchiveChange"
    />

    <div class="flex flex-col gap-3 sm:flex-row">
      <Button
        variant="outline"
        class="w-full sm:w-auto"
        :disabled="exportMutation.isPending.value"
        @click="handleExport"
      >
        <LoaderCircle
          v-if="exportMutation.isPending.value"
          class="size-4 animate-spin"
          aria-hidden="true"
        />
        <Download v-else class="size-4" aria-hidden="true" />
        {{ t('settings.profile.dataTransfer.export') }}
      </Button>
      <Button
        variant="outline"
        class="w-full sm:w-auto"
        :disabled="importMutation.isPending.value"
        @click="pickArchive"
      >
        <LoaderCircle
          v-if="importMutation.isPending.value"
          class="size-4 animate-spin"
          aria-hidden="true"
        />
        <Upload v-else class="size-4" aria-hidden="true" />
        {{ t('settings.profile.dataTransfer.import') }}
      </Button>
    </div>

    <p class="text-hint">{{ t('settings.profile.dataTransfer.note') }}</p>
  </Card>
</template>
