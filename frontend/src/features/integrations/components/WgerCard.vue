<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { INTEGRATION_LOGOS } from '@/constants/integrationLogos'
import { apiFetch } from '@/services/http'
import { useToasts } from '@/composables/useToasts'

const { t } = useI18n()
const toasts = useToasts()
const baseUrl = ref('')
const apiKey = ref('')
const enabled = ref(false)
const loading = ref(true)
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await apiFetch<{ wger_base_url: string | null; wger_enabled: boolean }>(
      '/nutrition/wger/settings',
    )
    baseUrl.value = data.wger_base_url ?? ''
    apiKey.value = ''
    enabled.value = !!data.wger_enabled
  } catch {
  } finally {
    loading.value = false
  }
}
async function save() {
  saving.value = true
  try {
    await apiFetch('/nutrition/wger/settings', {
      method: 'PUT',
      body: JSON.stringify({
        wger_base_url: baseUrl.value || null,
        wger_api_key: apiKey.value || null,
        wger_enabled: enabled.value,
      }),
    })
    toasts.success(t('settings.integrations.wger.saved'))
  } catch {
    toasts.error(t('settings.integrations.saveFailed'))
  } finally {
    saving.value = false
  }
}
async function test() {
  try {
    await apiFetch('/nutrition/wger/test', {
      method: 'POST',
      body: JSON.stringify({ wger_base_url: baseUrl.value, wger_api_key: apiKey.value || null }),
    })
    toasts.success(t('settings.integrations.wger.testOk'))
  } catch (e: unknown) {
    toasts.error(e instanceof Error ? e.message : t('settings.integrations.wger.testFailed'))
  }
}
onMounted(load)
</script>
<template>
  <Card class="flex flex-col gap-3 p-4">
    <div class="flex items-center gap-3">
      <img
        :src="INTEGRATION_LOGOS.wger"
        alt="Wger"
        class="size-10 rounded-full object-contain bg-white p-1"
      />
      <div class="flex flex-col">
        <span class="font-medium">Wger</span>
        <span class="text-sm text-muted-foreground">{{
          t('settings.integrations.wger.subtitle')
        }}</span>
      </div>
      <img :src="INTEGRATION_LOGOS.wgerSvg" alt="" class="ml-auto h-8 w-auto opacity-80" />
    </div>
    <div v-if="loading" class="text-sm text-muted-foreground">
      {{ t('settings.integrations.wger.loading') }}
    </div>
    <template v-else>
      <div class="flex flex-col gap-2">
        <Label>Base URL</Label>
        <Input v-model="baseUrl" placeholder="https://wger.de/api/v2" />
        <Label>API Key (Token)</Label>
        <Input v-model="apiKey" type="password" placeholder="wger token" />
        <label class="flex items-center gap-2 text-sm"
          ><input type="checkbox" v-model="enabled" /> Enabled</label
        >
      </div>
      <div class="flex gap-2">
        <Button :disabled="saving" @click="save">Save</Button>
        <Button variant="outline" @click="test">Test</Button>
      </div>
    </template>
  </Card>
</template>
