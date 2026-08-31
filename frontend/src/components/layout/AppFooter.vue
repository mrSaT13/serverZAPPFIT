<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { GitBranch } from '@lucide/vue'

import { useAppConfig, useFeatureFlags } from '@/features/config/composables/useAppConfig'
import { INTEGRATION_LOGOS } from '@/constants/integrationLogos'

const { t } = useI18n()
const { config } = useAppConfig()
const { isEnabled } = useFeatureFlags()

const startYear = 2023
const yearRange = computed(() => {
  const current = new Date().getFullYear()
  return current === startYear ? `${startYear}` : `${startYear} - ${current}`
})
</script>

<template>
  <footer class="lg:border-t lg:border-border lg:bg-card">
    <div class="mx-auto flex w-full max-w-5xl flex-col items-center gap-3 px-3 py-6 text-center">
      <p
        class="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 text-sm text-muted-foreground"
      >
        <span>© {{ yearRange }} {{ config.branding.appName }}</span>
        <span aria-hidden="true">•</span>
        <a
          class="inline-flex items-center hover:text-foreground"
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          :aria-label="t('footer.repository')"
        >
          <GitBranch class="size-4" />
        </a>
        <span aria-hidden="true">•</span>
        <span>v0.21.0</span>
      </p>

      <p
        v-if="isEnabled('strava') || isEnabled('garmin')"
        class="flex flex-wrap items-center justify-center gap-3"
      >
        <img
          v-if="isEnabled('strava')"
          :src="INTEGRATION_LOGOS.strava"
          :alt="t('footer.compatibleStrava')"
          height="25"
          class="h-[25px] w-auto"
        />
        <img
          v-if="isEnabled('garmin')"
          :src="INTEGRATION_LOGOS.garmin"
          :alt="t('footer.worksGarmin')"
          height="25"
          class="h-[25px] w-auto"
        />
      </p>
    </div>
  </footer>
</template>
