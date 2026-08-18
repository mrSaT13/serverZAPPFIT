<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Eye, Pencil } from '@lucide/vue'

import { SafeHtml } from '@/components/federation'
import { inputFieldClass } from '@/components/ui/input'

withDefaults(
  defineProps<{
    /** Forwarded to the textarea so a wrapping `FormField` label resolves. */
    id?: string
    rows?: number
    maxlength?: number
    disabled?: boolean
  }>(),
  { rows: 3, maxlength: 2500, disabled: false },
)

const model = defineModel<string>({ default: '' })

const { t } = useI18n()
const showPreview = ref(false)
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <div class="flex items-center justify-between">
      <span class="text-caption">{{ t('app.markdownEditor.supported') }}</span>
      <button
        type="button"
        class="inline-flex items-center gap-1 rounded-input px-2 py-1 text-meta text-muted-foreground outline-none transition-colors hover:bg-accent hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/30 disabled:opacity-50"
        :disabled="disabled"
        @click="showPreview = !showPreview"
      >
        <Pencil v-if="showPreview" class="size-3.5" />
        <Eye v-else class="size-3.5" />
        {{ showPreview ? t('app.markdownEditor.edit') : t('app.markdownEditor.preview') }}
      </button>
    </div>

    <textarea
      v-if="!showPreview"
      :id="id"
      v-model="model"
      :class="[inputFieldClass, 'w-full']"
      :rows="rows"
      :maxlength="maxlength"
      :disabled="disabled"
    />
    <div v-else class="min-h-24 rounded-input border border-border bg-muted/40 p-3">
      <SafeHtml v-if="model.trim()" :source="model" markdown class="text-body" />
      <p v-else class="text-meta text-muted-foreground">{{ t('app.markdownEditor.empty') }}</p>
    </div>
  </div>
</template>
