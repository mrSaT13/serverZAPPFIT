<script setup lang="ts">
import { RotateCw, TriangleAlert } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import LocaleSwitcher from '@/components/LocaleSwitcher.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { Button } from '@/components/ui/button'
import { getRuntimeBackendHost } from '@/services/runtime'

const { t } = useI18n()

// Surface the resolved host verbatim so operators can confirm exactly what the
// frontend read from `/env.js` against what they configured.
const configuredHost = getRuntimeBackendHost()

// Full reload re-runs bootstrap, which re-reads `/env.js` and re-attempts the
// config fetch — the natural way to recover after fixing ENDURAIN_HOST.
function reloadPage(): void {
  window.location.reload()
}
</script>

<template>
  <div
    class="flex min-h-svh flex-col items-center justify-center bg-background p-4 text-foreground"
  >
    <div class="w-full max-w-xl rounded-card border border-border bg-card p-6 text-center sm:p-8">
      <!-- Language and theme controls live in the card and stay usable even
           when the backend is unreachable; both are backend-independent. -->
      <div
        class="mb-6 flex flex-wrap items-center justify-center gap-3 border-b border-border pb-5"
      >
        <LocaleSwitcher />
        <ThemeToggle />
      </div>
      <div role="alert">
        <div class="mb-4 flex justify-center text-destructive">
          <TriangleAlert class="size-10" aria-hidden="true" />
        </div>
        <h1 class="mb-3 text-section-heading">{{ t('app.configError.title') }}</h1>
        <p class="mb-4 text-body">{{ t('app.configError.message') }}</p>
        <div
          class="mb-4 select-all break-all rounded-card border border-border bg-muted-foreground/10 px-3 py-2 text-left font-mono text-sm"
        >
          <span class="font-medium">ENDURAIN_HOST</span>:
          {{ configuredHost || t('app.configError.notSet') }}
        </div>
        <p class="text-body">{{ t('app.configError.help') }}</p>
      </div>

      <Button class="mt-5" @click="reloadPage">
        <RotateCw class="size-4" aria-hidden="true" />
        {{ t('app.configError.reload') }}
      </Button>
    </div>
  </div>
</template>
