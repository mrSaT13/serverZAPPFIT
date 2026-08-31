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

async function load(){
  loading.value=true
  try{
    const data:any = await apiFetch('/nutrition/wger\settings')
    baseUrl.value = data.wger_base_url ?? ''
    apiKey.value = ''
    enabled.value = !!data.wger_enabled
  }catch{ } finally{ loading.value=false }
}
async function save(){
  saving.value=true
  try{
    await apiFetch('/nutrition/wger\settings', { method:'PUT', body: JSON.stringify({ wger_base_url: baseUrl.value || null, wger_api_key: apiKey.value || null, wger_enabled: enabled.value }) })
    toasts.success('Wger saved')
  }catch{ toasts.error('Save failed') } finally{ saving.value=false }
}
async function test(){
  try{
    await apiFetch('/nutrition/wger\test', { method:'POST' })
    toasts.success('Wger OK')
  }catch(e:any){ toasts.error(e.message || 'Test failed') }
}
onMounted(load)
</script>
<template>
  <Card class="flex flex-col gap-3 p-4">
    <div class="flex items-center gap-3">
      <img :src="INTEGRATION_LOGOS.wger" alt="Wger" class="size-10 rounded-full object-contain bg-white p-1" />
      <div class="flex flex-col">
        <span class="font-medium">Wger</span>
        <span class="text-sm text-muted-foreground">Nutrition sync (optional, OFF is default)</span>
      </div>
      <img :src="INTEGRATION_LOGOS.wgerSvg" alt="" class="ml-auto h-8 w-auto opacity-80" />
    </div>
    <div v-if="loading" class="text-sm text-muted-foreground">Loading...</div>
    <template v-else>
      <div class="flex flex-col gap-2">
        <Label>Base URL</Label>
        <Input v-model="baseUrl" placeholder="https://wger.de\api\v2" />
        <Label>API Key (Token)</Label>
        <Input v-model="apiKey" type="password" placeholder="wger token" />
        <label class="flex items-center gap-2 text-sm"><input type="checkbox" v-model="enabled" /> Enabled</label>
      </div>
      <div class="flex gap-2">
        <Button :disabled="saving" @click="save">Save</Button>
        <Button variant="outline" @click="test">Test</Button>
      </div>
    </template>
  </Card>
</template>

