<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronLeft, ChevronRight, Image as ImageIcon, Trash2, Upload } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useToasts } from '@/composables/useToasts'
import { apiFetch } from '@/services/http'

interface GearImage {
  id: number
  gear_id: number
  image_path: string
  image_url: string | null
  created_at: string | null
}

const props = defineProps<{
  gearId: number
  images: GearImage[]
  canEdit: boolean
}>()

const emit = defineEmits<{
  uploaded: []
  deleted: [id: number]
}>()

const { t } = useI18n()
const toasts = useToasts()
const current = ref(0)
const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)

const hasImages = computed(() => props.images.length > 0)
const currentImage = computed(() => props.images[current.value] ?? null)

function resolveUrl(img: GearImage): string {
  if (img.image_url) return img.image_url
  return img.image_path
}

function prev(): void {
  if (props.images.length === 0) return
  current.value = (current.value - 1 + props.images.length) % props.images.length
}
function next(): void {
  if (props.images.length === 0) return
  current.value = (current.value + 1) % props.images.length
}

async function onFileChange(e: Event): Promise<void> {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    await apiFetch(`/gear_images/upload/gear/${props.gearId}`, { method: 'POST', body: fd, responseType: 'void' })
    toasts.success(t('gears.images.uploadSuccess'))
    emit('uploaded')
  } catch {
    toasts.error(t('gears.images.uploadError'))
  } finally {
    uploading.value = false
    if (input) input.value = ''
  }
}

async function deleteCurrent(): Promise<void> {
  const img = currentImage.value
  if (!img) return
  try {
    await apiFetch(`/gear_images/${img.id}`, { method: 'DELETE', responseType: 'void' })
    emit('deleted', img.id)
    if (current.value >= props.images.length - 1) current.value = Math.max(0, props.images.length - 2)
    toasts.success(t('gears.images.deleteSuccess'))
  } catch {
    toasts.error(t('gears.images.deleteError'))
  }
}
</script>

<template>
  <Card class="overflow-hidden">
    <div class="flex items-center justify-between px-4 py-3">
      <h3 class="text-card-heading flex items-center gap-2">
        <ImageIcon class="size-4" /> {{ t('gears.images.title') }}
      </h3>
      <Button v-if="canEdit" size="sm" variant="outline" :disabled="uploading" @click="fileInput?.click()">
        <Upload class="size-4" /> {{ t('gears.images.add') }}
      </Button>
      <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onFileChange" />
    </div>

    <div v-if="!hasImages" class="px-4 pb-4 text-body text-muted-foreground">
      {{ t('gears.images.empty') }}
    </div>

    <div v-else class="relative">
      <div class="aspect-[16/10] bg-muted flex items-center justify-center overflow-hidden">
        <img :src="resolveUrl(currentImage!)" :alt="t('gears.images.alt')" class="h-full w-full object-cover" />
      </div>

      <button v-if="images.length > 1" class="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white" @click="prev">
        <ChevronLeft class="size-5" />
      </button>
      <button v-if="images.length > 1" class="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white" @click="next">
        <ChevronRight class="size-5" />
      </button>

      <div class="flex items-center justify-between px-4 py-2">
        <span class="text-hint">{{ current + 1 }} / {{ images.length }}</span>
        <div class="flex gap-2">
          <span
            v-for="(img, idx) in images"
            :key="img.id"
            class="h-1.5 w-6 rounded-full"
            :class="idx === current ? 'bg-primary' : 'bg-border'"
          />
        </div>
        <Button v-if="canEdit" size="sm" variant="destructive" @click="deleteCurrent">
          <Trash2 class="size-4" /> {{ t('gears.images.delete') }}
        </Button>
      </div>

      <div class="flex gap-2 overflow-x-auto px-4 pb-3">
        <button
          v-for="(img, idx) in images"
          :key="img.id"
          class="h-16 w-24 shrink-0 overflow-hidden rounded-input border-2"
          :class="idx === current ? 'border-primary' : 'border-transparent'"
          @click="current = idx"
        >
          <img :src="resolveUrl(img)" class="h-full w-full object-cover" />
        </button>
      </div>
    </div>
  </Card>
</template>
