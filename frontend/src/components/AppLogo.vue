<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { useTheme } from '@/composables/useTheme'

const props = defineProps<{ alt?: string }>()

const { t } = useI18n()
const { theme } = useTheme()

// Defaults to the localized brand alt for standalone use. Pass `alt=""` where the
// logo sits next to the app name as text (decorative — avoids announcing it twice).
const altText = computed(() => props.alt ?? t('app.logoAlt'))

/** Theme-aware brand mark: light artwork on light surfaces, dark on dark. */
const src = computed(() => (theme.value === 'dark' ? '/logo_dark.svg' : '/logo_light.svg'))
</script>

<template>
  <img :src="src" :alt="altText" class="rounded" />
</template>
