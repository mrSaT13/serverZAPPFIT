<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Moon, Sun } from '@lucide/vue'

import { Button } from '@/components/ui/button'
import { useTheme } from '@/composables/useTheme'

const { t } = useI18n()
const { theme, toggle } = useTheme()

const toggleLabel = computed(() =>
  theme.value === 'dark' ? t('app.theme.toLight') : t('app.theme.toDark'),
)
const themeIcon = computed(() => (theme.value === 'dark' ? Moon : Sun))
</script>

<template>
  <Button
    variant="outline"
    size="icon-sm"
    :aria-label="toggleLabel"
    :title="toggleLabel"
    @click="toggle"
  >
    <component :is="themeIcon" class="size-4" aria-hidden="true" />
  </Button>
</template>
