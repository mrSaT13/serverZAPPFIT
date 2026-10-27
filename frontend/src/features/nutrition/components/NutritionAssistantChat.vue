<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { SendHorizonal, LoaderCircle, Sparkles } from '@lucide/vue'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { SafeHtml } from '@/components/federation'
import { useToasts } from '@/composables/useToasts'
import { aiChat, fetchAiStatus, type AiChatMessage, type AiStatus } from '@/features/nutrition/services/nutrition'

const { t, locale } = useI18n()
const toasts = useToasts()

const status = ref<AiStatus | null>(null)
const messages = ref<AiChatMessage[]>([])
const draft = ref('')
const pending = ref(false)
const historyEl = ref<HTMLElement | null>(null)

onMounted(async () => {
  try {
    status.value = await fetchAiStatus()
  } catch {
    status.value = { enabled: false, configured: false, model: null }
  }
})

async function send() {
  const text = draft.value.trim()
  if (!text || pending.value) return
  draft.value = ''
  messages.value.push({ role: 'user', content: text })
  pending.value = true
  await scrollDown()
  try {
    // Stateless multi-turn: send the recent window, the server prepends the
    // fresh data snapshot and the system prompt on every call.
    const recent = messages.value.slice(-16)
    const reply = await aiChat(recent, locale.value)
    messages.value.push({ role: 'assistant', content: reply.reply })
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    toasts.error(`${t('health.nutrition.assistant.error')}: ${msg}`)
  } finally {
    pending.value = false
    await scrollDown()
  }
}

async function scrollDown() {
  await nextTick()
  historyEl.value?.scrollTo({ top: historyEl.value.scrollHeight, behavior: 'smooth' })
}
</script>

<template>
  <Card v-if="status?.configured" class="flex flex-col gap-3">
    <div class="flex items-center gap-2">
      <Sparkles class="size-5" />
      <div class="text-card-heading">{{ t('health.nutrition.assistant.title') }}</div>
      <span v-if="status.model" class="text-hint">{{ status.model }}</span>
    </div>

    <div ref="historyEl" class="flex flex-col gap-2 max-h-[420px] overflow-auto">
      <div class="text-hint">{{ t('health.nutrition.assistant.greeting') }}</div>
      <div
        v-for="(m, i) in messages"
        :key="i"
        class="rounded-input border px-3 py-2 max-w-[90%]"
        :class="m.role === 'user' ? 'self-end bg-muted' : 'self-start'"
      >
        <SafeHtml v-if="m.role === 'assistant'" :source="m.content" markdown class="text-body" />
        <span v-else class="text-body whitespace-pre-wrap">{{ m.content }}</span>
      </div>
      <div v-if="pending" class="self-start text-hint flex items-center gap-2">
        <LoaderCircle class="size-4 animate-spin" /> {{ t('health.nutrition.assistant.thinking') }}
      </div>
    </div>

    <div class="flex gap-2">
      <Input
        v-model="draft"
        :placeholder="t('health.nutrition.assistant.placeholder')"
        :disabled="pending"
        @keydown.enter="send"
      />
      <Button variant="secondary" :disabled="pending || !draft.trim()" @click="send">
        <LoaderCircle v-if="pending" class="size-4 animate-spin" />
        <SendHorizonal v-else class="size-4" />
        <span class="sr-only">{{ t('health.nutrition.assistant.send') }}</span>
      </Button>
    </div>
  </Card>

  <Card v-else class="p-3 text-hint">
    {{ t('health.nutrition.assistant.disabled') }}
  </Card>
</template>
