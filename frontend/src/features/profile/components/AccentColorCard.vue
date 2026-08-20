<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Check } from '@lucide/vue'

import { Card } from '@/components/ui/card'
import { useTheme } from '@/composables/useTheme'

const { t } = useI18n()
const { accentId, accentPresets, setAccentColor } = useTheme()

/** Raw hex map for the preview dots. */
const PREVIEW_HEX: Record<string, string> = {
  blue: '#2563eb',
  green: '#16a34a',
  purple: '#7c3aed',
  orange: '#ea580c',
  red: '#dc2626',
  teal: '#0d9488',
  pink: '#db2777',
  indigo: '#4f46e5',
  amber: '#d97706',
}
</script>

<template>
  <Card class="flex flex-col gap-3">
    <div class="flex flex-col gap-1">
      <h2 class="text-card-heading">{{ t('settings.profile.accentColor.title') }}</h2>
      <p class="text-body">{{ t('settings.profile.accentColor.subtitle') }}</p>
    </div>

    <div class="grid grid-cols-5 gap-3 sm:grid-cols-9">
      <button
        v-for="preset in accentPresets"
        :key="preset.id"
        type="button"
        class="flex flex-col items-center gap-1.5 rounded-lg p-2 transition-colors hover:bg-accent"
        :class="accentId === preset.id ? 'ring-2 ring-primary ring-offset-2 ring-offset-background' : ''"
        :title="preset.label"
        @click="setAccentColor(preset.id)"
      >
        <span
          class="flex size-8 items-center justify-center rounded-full border border-border"
          :style="{ backgroundColor: PREVIEW_HEX[preset.id] }"
        >
          <Check
            v-if="accentId === preset.id"
            class="size-4 text-white"
            aria-hidden="true"
          />
        </span>
        <span class="text-meta text-muted-foreground">{{ preset.label }}</span>
      </button>
    </div>
  </Card>
</template>
