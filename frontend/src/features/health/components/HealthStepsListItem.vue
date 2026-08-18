<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Pencil, Trash2 } from '@lucide/vue'

import type { StepsEntry } from '@/features/health/types'

import { Button } from '@/components/ui/button'
import { INTEGRATION_LOGOS } from '@/constants/integrationLogos'
import { formatHealthEntryDate, formatSteps } from '@/features/health/utils/healthFormat'

const props = defineProps<{
  /** The steps entry to render. */
  entry: StepsEntry
}>()
const emit = defineEmits<{ edit: [entry: StepsEntry]; delete: [entry: StepsEntry] }>()

const { t, locale } = useI18n()

/** Primary steps string, or an em dash when the entry carries no count. */
const stepsLabel = computed(() =>
  props.entry.steps === null ? '—' : formatSteps(props.entry.steps),
)

const dateLabel = computed(() => formatHealthEntryDate(props.entry.date, locale.value))
const fromGarmin = computed(() => props.entry.source === 'garmin')
</script>

<template>
  <div class="px-4 py-3">
    <div class="flex items-center justify-between gap-3">
      <div class="flex min-w-0 items-center gap-2">
        <p class="text-item-title">{{ stepsLabel }}</p>
      </div>
      <div class="flex shrink-0 items-center gap-1">
        <img
          v-if="fromGarmin"
          :src="INTEGRATION_LOGOS.garminApp"
          :alt="t('health.steps.sourceGarmin')"
          :title="t('health.steps.sourceGarmin')"
          class="size-4 shrink-0"
        />
        <Button
          variant="ghost"
          size="icon-sm"
          :aria-label="t('health.steps.actions.edit')"
          @click="emit('edit', entry)"
        >
          <Pencil class="size-4" aria-hidden="true" />
        </Button>
        <Button
          variant="ghostDestructive"
          size="icon-sm"
          :aria-label="t('health.steps.actions.delete')"
          @click="emit('delete', entry)"
        >
          <Trash2 class="size-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
    <p class="text-hint">{{ dateLabel }}</p>
  </div>
</template>
