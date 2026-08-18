<script setup lang="ts">
import { isSupportedLocale } from '@/i18n'
import { useLocale } from '@/composables/useLocale'

const { t, locale, availableLocales, setLocale } = useLocale()

async function onChange(event: Event): Promise<void> {
  const value = (event.target as HTMLSelectElement).value
  if (isSupportedLocale(value)) {
    await setLocale(value)
  }
}
</script>

<template>
  <div class="flex items-center gap-2">
    <label class="sr-only" for="locale-select">{{ t('app.language') }}</label>
    <select
      id="locale-select"
      :value="locale"
      class="rounded-input border border-input bg-background px-2 py-1.5 text-meta text-foreground"
      @change="onChange"
    >
      <option v-for="option in availableLocales" :key="option.code" :value="option.code">
        {{ option.label }}
      </option>
    </select>
  </div>
</template>
