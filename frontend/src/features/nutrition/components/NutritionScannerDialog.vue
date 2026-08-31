<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { Html5Qrcode } from 'html5-qrcode'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [v: boolean]; detected: [code: string] }>()

const error = ref<string | null>(null)
let scanner: Html5Qrcode | null = null
let running = false

async function start() {
  error.value = null
  try {
    scanner = new Html5Qrcode('nutrition-scanner')
    running = true
    await scanner.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: { width: 250, height: 250 } },
      (decoded) => {
        if (decoded) {
          stop()
          emit('detected', decoded)
          emit('update:open', false)
        }
      },
      () => {},
    )
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function stop() {
  if (scanner && running) {
    try { await scanner.stop(); } catch {}
    try { scanner.clear(); } catch {}
    running = false
    scanner = null
  }
}

watch(() => props.open, (v) => {
  if (v) start()
  else stop()
})

onBeforeUnmount(() => { void stop() })
</script>

<template>
  <Dialog :open="open" @update:open="(v: boolean) => emit('update:open', v)">
    <DialogContent class="max-w-[420px]">
      <DialogHeader><DialogTitle>Сканер штрих-кода</DialogTitle></DialogHeader>
      <div id="nutrition-scanner" class="w-full overflow-hidden rounded-input bg-black" style="min-height: 260px" />
      <p v-if="error" class="text-hint text-destructive">{{ error }}</p>
      <div class="flex justify-end gap-2">
        <Button variant="outline" @click="emit('update:open', false)">Закрыть</Button>
      </div>
      <!-- Fallback for desktop without camera: manual entry handled in parent -->
    </DialogContent>
  </Dialog>
</template>
