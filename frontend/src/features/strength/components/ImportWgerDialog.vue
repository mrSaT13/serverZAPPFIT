<!-- Import plans from the user's own wger instance (optional integration). -->
<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Download } from '@lucide/vue'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import {
  importWgerRoutine,
  previewWgerRoutines,
  type WgerRoutinePreview,
} from '@/features/strength/services/workouts'
import { INTEGRATION_LOGOS } from '@/constants/integrationLogos'
import { useToasts } from '@/composables/useToasts'

const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ imported: [] }>()

const { t } = useI18n()
const toasts = useToasts()

const routines = ref<WgerRoutinePreview[]>([])
const loading = ref(false)
const importingId = ref<number | null>(null)
const loadError = ref<string | null>(null)

async function load(): Promise<void> {
  loading.value = true
  loadError.value = null
  try {
    routines.value = await previewWgerRoutines()
  } catch (e: unknown) {
    loadError.value = (e as Error)?.message ?? t('workouts.import.loadError')
    routines.value = []
  } finally {
    loading.value = false
  }
}

watch(open, (v) => {
  if (v) void load()
})

async function importOne(r: WgerRoutinePreview): Promise<void> {
  importingId.value = r.wger_id
  try {
    await importWgerRoutine(r.wger_id)
    toasts.success(t('workouts.import.done'))
    emit('imported')
    open.value = false
  } catch (e: unknown) {
    toasts.error((e as Error)?.message ?? t('workouts.import.error'))
  } finally {
    importingId.value = null
  }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="max-w-lg">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2">
          <img :src="INTEGRATION_LOGOS.wgerSvg" alt="wger" class="h-5 w-auto" />
          {{ t('workouts.import.title') }}
        </DialogTitle>
      </DialogHeader>

      <p class="text-hint">{{ t('workouts.import.hint') }}</p>

      <div v-if="loading" class="flex flex-col gap-2">
        <Skeleton v-for="i in 3" :key="i" class="h-12 w-full" />
      </div>
      <div v-else-if="loadError" class="flex flex-col gap-3">
        <div class="text-body text-destructive">{{ loadError }}</div>
        <Button variant="outline" size="sm" @click="load">{{ t('app.error.retry') }}</Button>
      </div>
      <div v-else class="flex max-h-[40vh] flex-col gap-1 overflow-auto">
        <div
          v-for="r in routines"
          :key="r.wger_id"
          class="flex items-center gap-2 rounded-input border px-3 py-2"
        >
          <div class="flex min-w-0 flex-col">
            <span class="truncate text-body font-medium">{{
              r.name || t('workouts.import.unnamed')
            }}</span>
            <span class="text-hint">
              {{ r.days }} {{ t('workouts.plan.days') }}
              <template v-if="r.is_template"> · {{ t('workouts.import.template') }}</template>
              <template v-if="r.start"> · {{ r.start }}</template>
            </span>
          </div>
          <Button
            class="ml-auto"
            size="sm"
            :variant="'secondary'"
            :disabled="importingId !== null"
            @click="importOne(r)"
          >
            <Download v-if="importingId !== r.wger_id" class="size-4" />
            {{
              importingId === r.wger_id ? t('workouts.import.working') : t('workouts.import.button')
            }}
          </Button>
        </div>
        <div v-if="routines.length === 0" class="text-hint py-6 text-center">
          {{ t('workouts.import.empty') }}
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
