<!-- Session logging dialog: pick date/plan, add set rows, save once. When a
plan is provided its prescription prefills the target rows. -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Trash2 } from '@lucide/vue'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import ExercisePickerDialog from './ExercisePickerDialog.vue'
import { createSession, type WorkoutPlan } from '@/features/strength/services/workouts'
import { useToasts } from '@/composables/useToasts'

const props = defineProps<{ plan: WorkoutPlan | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [] }>()

const { t } = useI18n()
const toasts = useToasts()

const today = new Date().toISOString().slice(0, 10)
const date = ref(today)
const durationMin = ref('60')
const comment = ref('')

interface DraftSetRow {
  key: number
  exerciseName: string
  setNo: string
  weightKg: string
  reps: string
  completed: boolean
}

const rows = ref<DraftSetRow[]>([])
const pickerOpen = ref(false)
let keySeq = 1

const planNames = computed(() => props.plan?.exercises ?? [])

function addRow(name = planNames.value[0]?.name ?? ''): void {
  const sameNameCount = rows.value.filter((r) => r.exerciseName === name).length
  rows.value.push({
    key: keySeq++,
    exerciseName: name,
    setNo: String(sameNameCount + 1),
    weightKg: '',
    reps: '',
    completed: true,
  })
}

// Prefill from the plan prescription when the dialog opens for a plan.
watch(
  () => props.plan,
  (plan) => {
    rows.value = []
    comment.value = plan?.name ?? ''
    if (!plan) return
    for (const ex of plan.exercises) {
      for (let i = 0; i < (ex.target_sets ?? 1); i++) {
        rows.value.push({
          key: keySeq++,
          exerciseName: ex.name,
          setNo: String(i + 1),
          weightKg: ex.target_weight_kg?.toString() ?? '',
          reps: '',
          completed: true,
        })
      }
    }
  },
  { immediate: true },
)

watch(open, (v) => {
  if (v && rows.value.length === 0) addRow()
})

function num(value: string): number | null {
  if (!String(value).trim()) return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

async function save(): Promise<void> {
  try {
    await createSession({
      date: date.value,
      plan_id: props.plan?.id ?? null,
      duration_min: num(durationMin.value),
      comment: comment.value.trim() || null,
      sets: rows.value.map((r) => ({
        exercise_name: r.exerciseName,
        set_no: num(r.setNo) ?? 1,
        weight_kg: num(r.weightKg),
        reps: num(r.reps),
        completed: r.completed,
      })),
    })
    emit('saved')
    open.value = false
  } catch (e: unknown) {
    toasts.error((e as Error)?.message || t('workouts.session.saveError'))
  }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="max-w-2xl">
      <DialogHeader>
        <DialogTitle>{{ props.plan ? t('workouts.session.start') : t('workouts.session.logEmpty') }}</DialogTitle>
      </DialogHeader>

      <div class="grid grid-cols-3 gap-2">
        <div class="flex flex-col gap-1">
          <Label>{{ t('workouts.session.date') }}</Label>
          <Input v-model="date" type="date" />
        </div>
        <div class="flex flex-col gap-1">
          <Label>{{ t('workouts.session.duration') }}</Label>
          <Input v-model="durationMin" type="number" />
        </div>
        <div class="flex flex-col gap-1">
          <Label>{{ t('workouts.session.comment') }}</Label>
          <Input v-model="comment" :placeholder="t('workouts.session.commentPlaceholder')" />
        </div>
      </div>

      <div class="flex max-h-[40vh] flex-col gap-1 overflow-auto">
        <div
          v-for="(row, idx) in rows"
          :key="row.key"
          class="grid grid-cols-[1fr_4rem_5rem_5rem_auto] items-end gap-2 rounded-input border p-2"
        >
          <div class="flex flex-col gap-1">
            <Label class="sr-only">{{ t('workouts.session.exercise') }}</Label>
            <Input v-model="row.exerciseName" :placeholder="t('workouts.session.exercise')" />
          </div>
          <Input v-model="row.setNo" type="number" :placeholder="t('workouts.plan.sets')" />
          <Input v-model="row.weightKg" type="number" step="0.1" :placeholder="t('workouts.plan.weightKg')" />
          <Input v-model="row.reps" type="number" :placeholder="t('workouts.plan.reps')" />
          <Button size="sm" variant="ghost" class="text-destructive" @click="rows.splice(idx, 1)">
            <Trash2 class="size-4" />
          </Button>
        </div>
      </div>

      <div class="flex justify-between">
        <Button size="sm" variant="outline" @click="pickerOpen = true">
          <Plus class="size-4" /> {{ t('workouts.session.addSet') }}
        </Button>
        <div class="flex gap-2">
          <Button variant="outline" @click="open = false">{{ t('workouts.form.cancel') }}</Button>
          <Button @click="save">{{ t('workouts.form.save') }}</Button>
        </div>
      </div>

      <ExercisePickerDialog v-model:open="pickerOpen" @picked="(ex) => addRow(ex.name)" />
    </DialogContent>
  </Dialog>
</template>
