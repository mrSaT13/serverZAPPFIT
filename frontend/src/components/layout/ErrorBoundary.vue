<script setup lang="ts">
import { onErrorCaptured, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { Button } from '@/components/ui/button'
import { useTelemetry } from '@/composables/useTelemetry'

const { t } = useI18n()
const route = useRoute()
const hasError = ref(false)

onErrorCaptured((error) => {
  hasError.value = true
  useTelemetry().captureError(error, { scope: 'ErrorBoundary' })
  // Contain the error here so a single broken view doesn't blank the app shell.
  return false
})

// Recover automatically when the user navigates to another route.
watch(
  () => route.fullPath,
  () => {
    hasError.value = false
  },
)

/** Clears the error state to re-attempt rendering the current view. */
function reset(): void {
  hasError.value = false
}
</script>

<template>
  <div v-if="hasError" class="flex flex-col items-center gap-3 py-12 text-center" role="alert">
    <h2 class="text-section-heading">{{ t('app.error.title') }}</h2>
    <p class="max-w-md text-body">{{ t('app.error.message') }}</p>
    <Button @click="reset">{{ t('app.error.retry') }}</Button>
  </div>
  <slot v-else />
</template>
