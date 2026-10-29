/** * Exercise picker dialog— searches the offline (baked wger) catalog and * returns the chosen
exercise to the plan editor. */
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Dumbbell, Info, Search, X } from '@lucide/vue'

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  catalogDescriptionText,
  searchCatalog,
  fetchCatalogMeta,
  type CatalogExercise,
  type CatalogMeta,
} from '@/features/strength/services/workouts'

const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ picked: [exercise: CatalogExercise] }>()

const { t, locale } = useI18n()

const q = ref('')
const meta = ref<CatalogMeta | null>(null)
const results = ref<CatalogExercise[]>([])
const loading = ref(false)
/** Set when the catalog endpoint failed (e.g. snapshot missing on the server). */
const loadError = ref(false)
// '' === "all"; Select values are plain strings.
const categoryId = ref<string>('')
const equipmentId = ref<string>('')

/** The offline snapshot was never seeded into this server's database. */
const notSeeded = computed(() => (meta.value?.counts.seedError ?? 0) === 1)

/** Prefers the UI language's translation, falls back to English (always present). */
function displayName(exercise: CatalogExercise): string {
  const lang = locale.value.split('-')[0] ?? 'en'
  const tr =
    (exercise.translations as Record<string, { name: string } | undefined>)[lang] ??
    exercise.translations.en
  return tr?.name ?? exercise.name
}

/** UI language code for language-scoped catalog search. */
const searchLang = computed(() => locale.value.split('-')[0] ?? 'en')

/** First technique tip in the UI language (English fallback), if any. */
function displayTip(exercise: CatalogExercise): string | null {
  const lang = locale.value.split('-')[0] ?? 'en'
  const tips = exercise.tips ?? {}
  return tips[lang]?.[0] ?? tips.en?.[0] ?? null
}

/** wger_id of the exercise whose "how to perform" block is expanded. */
const expandedId = ref<number | null>(null)

/** First tips entry for the expanded exercise, matching the description's language. */
function expandedTips(exercise: CatalogExercise): string[] {
  const lang = locale.value.split('-')[0] ?? 'en'
  const tips = exercise.tips ?? {}
  return tips[lang] ?? tips.en ?? []
}

function toggleDetails(exercise: CatalogExercise): void {
  expandedId.value = expandedId.value === exercise.wger_id ? null : exercise.wger_id
}

async function runSearch(): Promise<void> {
  loading.value = true
  loadError.value = false
  try {
    if (!meta.value) meta.value = await fetchCatalogMeta()
    const data = await searchCatalog(q.value, {
      category_id: categoryId.value !== '' ? Number(categoryId.value) : undefined,
      equipment_id: equipmentId.value !== '' ? Number(equipmentId.value) : undefined,
      lang: searchLang.value,
    })
    results.value = data.records
  } catch {
    loadError.value = true
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
// Re-run the search when the user switches language so names/sort follow.
watch(searchLang, () => {
  expandedId.value = null
  return runSearch()
})
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
        <div v-for="ex in results" :key="ex.wger_id" class="rounded-input border">
          <div class="flex items-center gap-1 pr-1">
            <button
              class="min-w-0 flex-1 rounded-input px-3 py-2 text-left hover:bg-muted"
              @click="emit('picked', ex)"
            >
              <div class="flex items-center gap-2">
                <Dumbbell class="size-4 shrink-0 opacity-60" />
                <div class="flex min-w-0 flex-col">
                  <span class="truncate text-body font-medium">{{ displayName(ex) }}</span>
                  <span class="text-hint">
                    {{ ex.category ? t(`workouts.catalog.categories.${ex.category.name}`) : '' }}
                    <template v-if="ex.muscles.length">
                      ·
                      {{
                        ex.muscles
                          .map((m) => t(`workouts.catalog.muscles.${m.name_en || m.name}`))
                          .join(', ')
                      }}</template
                    >
                  </span>
                  <span v-if="displayTip(ex)" class="text-hint truncate italic">{{
                    displayTip(ex)
                  }}</span>
                </div>
              </div>
            </button>
            <button
              v-if="catalogDescriptionText(ex, searchLang) || expandedId === ex.wger_id"
              class="flex size-7 items-center justify-center rounded-full text-muted-foreground hover:bg-muted"
              :aria-label="
                expandedId === ex.wger_id
                  ? t('workouts.picker.closeDetails')
                  : t('workouts.picker.howToObject')
              "
              :aria-expanded="expandedId === ex.wger_id"
              @click="toggleDetails(ex)"
            >
              <X v-if="expandedId === ex.wger_id" class="size-4" />
              <Info v-else class="size-4" />
            </button>
          </div>
          <div v-if="expandedId === ex.wger_id" class="border-t px-3 py-2">
            <p class="text-hint mb-1 text-xs font-medium">
              {{ t('workouts.picker.howTo') }}
            </p>
            <template v-for="(desc, i) in [catalogDescriptionText(ex, searchLang)]" :key="i">
              <p v-if="desc?.fellBackToEnglish" class="text-hint mb-1 text-xs italic">
                {{ t('workouts.picker.englishOnly') }}
              </p>
              <p v-if="desc" class="text-body whitespace-pre-line text-sm">{{ desc.text }}</p>
            </template>
            <ul v-if="expandedTips(ex).length" class="mt-2 list-disc pl-4">
              <li v-for="tip in expandedTips(ex)" :key="tip" class="text-body text-sm">
                {{ tip }}
              </li>
            </ul>
          </div>
        </div>
        <div
          v-if="notSeeded"
          class="rounded-input border border-orange-300 bg-orange-50 px-3 py-2 text-hint text-orange-700"
        >
          {{ t('workouts.picker.notSeeded') }}
        </div>
        <div v-else-if="loadError" class="text-hint py-6 text-center text-destructive">
          {{ t('workouts.picker.loadError') }}
        </div>
        <div v-else-if="results.length === 0" class="text-hint py-6 text-center">
          {{ t('workouts.picker.empty') }}
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
