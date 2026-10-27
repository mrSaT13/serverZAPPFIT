/**
 * Exercise picker dialog— searches the offline (baked wger) catalog and
 * returns the chosen exercise to the plan editor.
 */
<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Dumbbell, Search } from '@lucide/vue'

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { searchCatalog, fetchCatalogMeta, type CatalogExercise, type CatalogMeta } from '@/features/strength/services/workouts'

const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ picked: [exercise: CatalogExercise] }>()

const { t, locale } = useI18n()

const q = ref('')
const meta = ref<CatalogMeta | null>(null)
const results = ref<CatalogExercise[]>([])
const loading = ref(false)
// '' === "all"; Select values are plain strings.
const categoryId = ref<string>('')
const equipmentId = ref<string>('')

/** Prefers the UI language's translation, falls back to English (always present). */
function displayName(exercise: CatalogExercise): string {
  const lang = locale.value.split('-')[0] ?? 'en'
  const tr =
    (exercise.translations as Record<string, { name: string } | undefined>)[lang] ??
    exercise.translations.en
  return tr?.name ?? exercise.name
}

async function runSearch(): Promise<void> {
  loading.value = true
  try {
    if (!meta.value) meta.value = await fetchCatalogMeta()
    const data = await searchCatalog(q.value, {
      category_id: categoryId.value !== '' ? Number(categoryId.value) : undefined,
      equipment_id: equipmentId.value !== '' ? Number(equipmentId.value) : undefined,
    })
    results.value = data.records
  } catch {
    results.value = []
  } finally {
    loading.value = false
  }
}

let timer: ReturnType<typeof setTimeout> | undefined
watch(q, () => {
  clearTimeout(timer)
  timer = setTimeout(runSearch, 300)
})
watch([categoryId, equipmentId], runSearch)
watch(open, (v) => {
  if (v && results.value.length === 0) void runSearch()
})
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="max-w-xl">
      <DialogHeader>
        <DialogTitle>{{ t('workouts.picker.title') }}</DialogTitle>
      </DialogHeader>

      <div class="flex flex-wrap gap-2">
        <div class="relative min-w-48 flex-1">
          <Search class="absolute top-2.5 left-2 size-4 opacity-50" />
          <Input v-model="q" :placeholder="t('workouts.picker.searchPlaceholder')" class="pl-8" />
        </div>
        <Select v-model="categoryId">
          <option value="">{{ t('workouts.picker.allCategories') }}</option>
          <option v-for="c in meta?.categories ?? []" :key="c.id" :value="String(c.id)">
            {{ t(`workouts.catalog.categories.${c.name}`) }}
          </option>
        </Select>
        <Select v-model="equipmentId">
          <option value="">{{ t('workouts.picker.allEquipment') }}</option>
          <option v-for="e in meta?.equipment ?? []" :key="e.id" :value="String(e.id)">
            {{ t(`workouts.catalog.equipment.${e.name}`) }}
          </option>
        </Select>
      </div>

      <div v-if="loading" class="flex flex-col gap-2">
        <Skeleton class="h-12 w-full" v-for="i in 3" :key="i" />
      </div>
      <div v-else class="flex max-h-[50vh] flex-col gap-1 overflow-auto">
        <button
          v-for="ex in results"
          :key="ex.wger_id"
          class="text-left rounded-input border px-3 py-2 hover:bg-muted"
          @click="emit('picked', ex)"
        >
          <div class="flex items-center gap-2">
            <Dumbbell class="size-4 shrink-0 opacity-60" />
            <div class="flex min-w-0 flex-col">
              <span class="truncate text-body font-medium">{{ displayName(ex) }}</span>
              <span class="text-hint">
                {{ ex.category ? t(`workouts.catalog.categories.${ex.category.name}`) : '' }}
                <template v-if="ex.muscles.length"> · {{ ex.muscles.map((m) => t(`workouts.catalog.muscles.${m.name_en || m.name}`)).join(', ') }}</template>
              </span>
            </div>
          </div>
        </button>
        <div v-if="results.length === 0" class="text-hint py-6 text-center">
          {{ t('workouts.picker.empty') }}
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
