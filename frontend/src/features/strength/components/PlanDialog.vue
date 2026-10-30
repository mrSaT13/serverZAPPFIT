<!-- Plan create/edit dialog. Exercises are a flat ordered list, optionally
grouped by a day label; the picker sources them from the offline catalog. -->
<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Info, Languages, Plus, Sparkles, Trash2 } from '@lucide/vue'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { inputFieldClass } from '@/components/ui/input/fieldClasses'
import { Label } from '@/components/ui/label'
import ExercisePickerDialog from './ExercisePickerDialog.vue'
import {
  catalogDescriptionText,
  fetchAiPlanStatus,
  fetchCatalogExercise,
  generateAiPlan,
  translateExercise,
  type AiPlanDraft,
  type CatalogExercise,
  type PlanExercise,
  type WorkoutPlan,
} from '@/features/strength/services/workouts'

/** Wire-shaped plan body, shared between create and update. */
export interface PlanDialogSavePayload {
  name: string
  description: string | null
  exercises: PlanExercise[]
}

const props = defineProps<{ plan: WorkoutPlan | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [body: PlanDialogSavePayload] }>()

const { t, locale } = useI18n()

/** UI language where available, else canonical English name. */
function catalogName(ex: CatalogExercise): string {
  return (
    ex.translations[locale.value.split('-')[0] ?? 'en']?.name ?? ex.translations.en?.name ?? ex.name
  )
}

const name = ref('')
const description = ref('')
const pickerOpen = ref(false)

/** Draft row: inputs are strings; number casts happen on save. */
interface DraftRow {
  day_label: string
  name: string
  muscle_group: string | null
  wger_exercise_id: number | null
  notes: string | null
  target_sets: string
  target_reps: string
  target_weight_kg: string
  rest_s: string
}

const exercises = ref<DraftRow[]>([])

// ---- AI plan generation ----
const aiOpen = ref(false)
const aiPrompt = ref('')
const aiLoading = ref(false)
const aiError = ref<string | null>(null)
const aiDone = ref(false)
/** null = unknown yet; the status is fetched lazily on first open. */
const aiConfigured = ref<boolean | null>(null)

watch(aiOpen, (v) => {
  if (v && aiConfigured.value === null) {
    fetchAiPlanStatus()
      .then((s) => (aiConfigured.value = s.configured))
      .catch(() => (aiConfigured.value = false))
  }
  if (!v) aiDone.value = false
})

/** Replaces the editor contents with an AI-generated draft (review, then save). */
function applyAiDraft(draft: AiPlanDraft): void {
  name.value = draft.name?.trim() || name.value
  description.value = draft.description?.trim() || description.value
  exercises.value = draft.exercises.map(
    (ex): DraftRow => ({
      day_label: ex.day_label ?? '',
      name: ex.name,
      muscle_group: ex.muscle_group ?? null,
      wger_exercise_id: ex.wger_exercise_id ?? null,
      notes: ex.notes ?? null,
      target_sets: ex.target_sets?.toString() ?? '',
      target_reps: ex.target_reps ?? '',
      target_weight_kg: ex.target_weight_kg?.toString() ?? '',
      rest_s: ex.rest_s?.toString() ?? '',
    }),
  )
}

async function generate(): Promise<void> {
  if (!aiPrompt.value.trim() || aiLoading.value) return
  aiLoading.value = true
  aiError.value = null
  aiDone.value = false
  try {
    const draft = await generateAiPlan(aiPrompt.value.trim(), locale.value.split('-')[0])
    applyAiDraft(draft)
    aiDone.value = true
    aiPrompt.value = ''
  } catch (e: unknown) {
    aiError.value = (e as Error)?.message || t('workouts.ai.error')
  } finally {
    aiLoading.value = false
  }
}

watch(
  () => props.plan,
  (plan) => {
    name.value = plan?.name ?? ''
    description.value = plan?.description ?? ''
    exercises.value = (plan?.exercises ?? []).map(
      (e): DraftRow => ({
        day_label: e.day_label ?? '',
        name: e.name,
        muscle_group: e.muscle_group ?? null,
        wger_exercise_id: e.wger_exercise_id ?? null,
        notes: e.notes ?? null,
        target_sets: e.target_sets?.toString() ?? '',
        target_reps: e.target_reps ?? '',
        target_weight_kg: e.target_weight_kg?.toString() ?? '',
        rest_s: e.rest_s?.toString() ?? '',
      }),
    )
  },
  { immediate: true },
)

function num(value: string): number | null {
  if (!String(value).trim()) return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function previousDay(): string {
  const last = exercises.value[exercises.value.length - 1]
  return last?.day_label ?? ''
}

function onPicked(ex: CatalogExercise): void {
  exercises.value.push({
    day_label: previousDay(),
    name: catalogName(ex),
    wger_exercise_id: ex.wger_id,
    muscle_group: ex.category?.name ?? null,
    notes: null,
    target_sets: '',
    target_reps: '',
    target_weight_kg: '',
    rest_s: '',
  })
}

/** Per-row "how to" lookup: cached catalog exercise + expanded row index. */
const catalogCache = ref<Record<number, CatalogExercise>>({})
const expandedInfo = ref<number | null>(null)
const infoLoading = ref(false)
const infoError = ref(false)

/** On-demand RU translation cache (wger id → translated text). */
const ruTranslationCache = ref<Record<number, { description: string; tip: string | null }>>({})
const translatingIdx = ref<number | null>(null)
const translateFailed = ref(false)

/** Exercise description in the UI language (English fallback), if any. */
function rowDescription(wgerId: number): { text: string; fellBackToEnglish: boolean } | null {
  const ex = catalogCache.value[wgerId]
  if (!ex) return null
  return catalogDescriptionText(ex, locale.value.split('-')[0] ?? 'en')
}

/** First technique tips matching the description language, if any. */
function rowTips(wgerId: number): string[] {
  const ex = catalogCache.value[wgerId]
  if (!ex) return []
  const lang = locale.value.split('-')[0] ?? 'en'
  const tips = ex.tips ?? {}
  return tips[lang] ?? tips.en ?? []
}

async function toggleRowInfo(idx: number): Promise<void> {
  if (expandedInfo.value === idx) {
    expandedInfo.value = null
    return
  }
  const wgerId = exercises.value[idx]?.wger_exercise_id
  if (wgerId == null) return
  expandedInfo.value = idx
  if (!catalogCache.value[wgerId]) {
    infoLoading.value = true
    infoError.value = false
    try {
      catalogCache.value[wgerId] = await fetchCatalogExercise(wgerId)
    } catch {
      infoError.value = true
      return
    } finally {
      infoLoading.value = false
    }
  }
}

/** Whether the catalog itself carries a Russian description (EN fallback doesn't count). */
function hasRuDescription(wgerId: number): boolean {
  return Boolean(catalogCache.value[wgerId]?.translations.ru?.description?.trim())
}

/** Translated (or freshly translating) description for the expanded row. */
function shownDescription(wgerId: number): string | null {
  return ruTranslationCache.value[wgerId]?.description ?? rowDescription(wgerId)?.text ?? null
}

function shownTip(wgerId: number): string | null {
  return ruTranslationCache.value[wgerId]?.tip ?? (rowTips(wgerId)[0] as string | undefined) ?? null
}

async function translateRow(idx: number): Promise<void> {
  const wgerId = exercises.value[idx]?.wger_exercise_id
  if (wgerId == null || translatingIdx.value !== null) return
  if (ruTranslationCache.value[wgerId]) return
  translatingIdx.value = idx
  translateFailed.value = false
  try {
    const res = await translateExercise(wgerId)
    if (res.description.trim()) {
      ruTranslationCache.value[wgerId] = { description: res.description, tip: res.tip }
    } else {
      translateFailed.value = true
    }
  } catch {
    translateFailed.value = true
  } finally {
    translatingIdx.value = null
  }
}

function save(): void {
  const payload: PlanDialogSavePayload = {
    name: name.value.trim(),
    description: description.value.trim() || null,
    exercises: exercises.value.map((ex, idx) => ({
      position: idx,
      day_label: ex.day_label.trim() || null,
      name: ex.name,
      muscle_group: ex.muscle_group,
      wger_exercise_id: ex.wger_exercise_id,
      notes: ex.notes,
      target_sets: num(ex.target_sets),
      target_reps: ex.target_reps.trim() || null,
      target_weight_kg: num(ex.target_weight_kg),
      rest_s: num(ex.rest_s),
    })),
  }
  emit('saved', payload)
  open.value = false
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="max-w-2xl">
      <DialogHeader>
        <DialogTitle>{{
          props.plan ? t('workouts.plan.editTitle') : t('workouts.plan.createTitle')
        }}</DialogTitle>
      </DialogHeader>
      <div class="flex flex-col gap-2">
        <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div class="flex flex-col gap-1">
            <Label>{{ t('workouts.plan.name') }}</Label>
            <Input v-model="name" :placeholder="t('workouts.plan.namePlaceholder')" />
          </div>
          <div class="flex flex-col gap-1">
            <Label>{{ t('workouts.plan.description') }}</Label>
            <Input v-model="description" :placeholder="t('workouts.plan.descriptionPlaceholder')" />
          </div>
        </div>

        <div class="flex items-center justify-between">
          <span class="text-card-heading">{{ t('workouts.plan.exercises') }}</span>
          <div class="flex gap-2">
            <Button size="sm" variant="secondary" @click="aiOpen = !aiOpen">
              <Sparkles class="size-4" /> {{ t('workouts.ai.button') }}
            </Button>
            <Button size="sm" variant="outline" @click="pickerOpen = true">
              <Plus class="size-4" /> {{ t('workouts.plan.addExercise') }}
            </Button>
          </div>
        </div>

        <!-- AI generation panel: describe the goal, get a ready plan draft. -->
        <div v-if="aiOpen" class="rounded-input border bg-muted/40 p-3">
          <div class="mb-2 flex items-center gap-2">
            <Sparkles class="size-4 text-primary" />
            <span class="text-body font-medium">{{ t('workouts.ai.title') }}</span>
          </div>
          <div v-if="aiConfigured === false" class="text-hint mb-2 text-orange-500">
            {{ t('workouts.ai.notConfigured') }}
          </div>
          <template v-else>
            <div class="text-hint mb-2">{{ t('workouts.ai.hint') }}</div>
            <textarea
              v-model="aiPrompt"
              :class="inputFieldClass"
              rows="3"
              :placeholder="t('workouts.ai.promptPlaceholder')"
              :disabled="aiLoading"
              :maxlength="2000"
            ></textarea>
            <div class="mt-2 flex items-center gap-2">
              <Button
                size="sm"
                :disabled="aiLoading || aiPrompt.trim().length < 3"
                @click="generate"
              >
                <Sparkles class="size-4" />
                {{ aiLoading ? t('workouts.ai.generating') : t('workouts.ai.generate') }}
              </Button>
              <span v-if="aiDone" class="text-hint text-green-600">{{
                t('workouts.ai.applied')
              }}</span>
              <span v-if="aiError" class="text-hint text-destructive">{{ aiError }}</span>
            </div>
          </template>
        </div>

        <div class="flex max-h-[40vh] flex-col gap-1 overflow-auto">
          <div v-for="(ex, idx) in exercises" :key="idx" class="rounded-input border p-2">
            <div class="flex items-center gap-2">
              <span class="flex-1 truncate text-body font-medium">{{ ex.name }}</span>
              <Button
                v-if="ex.wger_exercise_id != null"
                size="sm"
                variant="ghost"
                :title="t('workouts.picker.howTo')"
                @click="toggleRowInfo(idx)"
              >
                <Info class="size-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                class="text-destructive"
                @click="
                  exercises.splice(idx, 1)
                  expandedInfo = null
                "
              >
                <Trash2 class="size-4" />
              </Button>
            </div>
            <div
              v-if="expandedInfo === idx && ex.wger_exercise_id != null"
              class="text-hint mt-1 rounded-input bg-muted/60 px-2 py-1 text-body"
            >
              <template v-if="infoLoading">…</template>
              <template v-else-if="shownDescription(ex.wger_exercise_id)">
                {{ shownDescription(ex.wger_exercise_id) }}
                <span
                  v-if="
                    !hasRuDescription(ex.wger_exercise_id) &&
                    !ruTranslationCache[ex.wger_exercise_id]
                  "
                  class="italic"
                >
                  ({{ t('workouts.picker.englishOnly') }})
                </span>
                <template v-if="shownTip(ex.wger_exercise_id)">
                  <br />{{ shownTip(ex.wger_exercise_id) }}
                </template>
              </template>
              <template v-else>{{ t('workouts.picker.loadError') }}</template>
              <div
                v-if="
                  !hasRuDescription(ex.wger_exercise_id) &&
                  !ruTranslationCache[ex.wger_exercise_id] &&
                  shownDescription(ex.wger_exercise_id)
                "
                class="mt-1"
              >
                <Button
                  size="sm"
                  variant="outline"
                  :disabled="translatingIdx !== null"
                  @click="translateRow(idx)"
                >
                  <Languages class="size-4" />
                  {{
                    translatingIdx === idx
                      ? t('workouts.picker.translating')
                      : t('workouts.picker.translate')
                  }}
                </Button>
                <span
                  v-if="translateFailed && translatingIdx === null"
                  class="text-destructive ml-2"
                >
                  {{ t('workouts.picker.translateFailed') }}
                </span>
              </div>
            </div>
            <div class="mt-1 grid grid-cols-2 gap-2 sm:grid-cols-5">
              <Input v-model="ex.day_label" :placeholder="t('workouts.plan.day')" />
              <Input
                v-model="ex.target_sets"
                :placeholder="t('workouts.plan.sets')"
                type="number"
              />
              <Input v-model="ex.target_reps" :placeholder="t('workouts.plan.reps')" />
              <Input
                v-model="ex.target_weight_kg"
                :placeholder="t('workouts.plan.weightKg')"
                type="number"
              />
              <Input v-model="ex.rest_s" :placeholder="t('workouts.plan.restS')" type="number" />
            </div>
          </div>
          <div v-if="exercises.length === 0" class="text-hint py-4 text-center">
            {{ t('workouts.plan.noExercises') }}
          </div>
        </div>
      </div>

      <div class="flex justify-end gap-2">
        <Button variant="outline" @click="open = false">{{ t('workouts.form.cancel') }}</Button>
        <Button @click="save">{{ t('workouts.form.save') }}</Button>
      </div>

      <ExercisePickerDialog v-model:open="pickerOpen" @picked="onPicked" />
    </DialogContent>
  </Dialog>
</template>
