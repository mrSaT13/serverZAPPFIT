<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type {
  ActivityExerciseTitle,
  ActivityWorkoutSet,
  ActivityWorkoutStep,
} from '@/features/activities/types'

import { formatHmsDuration } from '@/features/activities/utils/format'
import { expandWorkoutSteps, resolveExerciseName } from '@/features/activities/utils/workout'

const props = defineProps<{
  workoutSteps: ActivityWorkoutStep[]
  workoutSets: ActivityWorkoutSet[]
  exerciseTitles: ActivityExerciseTitle[]
}>()

const { t } = useI18n()

interface StepRow {
  index: number
  intensity: string | null
  duration: string | null
  reps: number | null
  exercise: string | null
  stroke: string | null
}

const stepRows = computed<StepRow[]>(() =>
  expandWorkoutSteps(props.workoutSteps).map((step, index) => ({
    index: index + 1,
    intensity: step.intensity,
    duration:
      step.durationType === 'time' && step.durationValue !== null
        ? formatHmsDuration(step.durationValue)
        : null,
    reps: step.durationType === 'reps' ? step.durationValue : null,
    exercise: resolveExerciseName(props.exerciseTitles, step.exerciseName, step.exerciseCategory),
    stroke: step.targetType === 'swim_stroke' ? step.secondaryTargetValue : null,
  })),
)

interface SetRow {
  index: number
  setType: string
  duration: string
  reps: number | null
  exercise: string | null
  weight: number | null
}

const setRows = computed<SetRow[]>(() =>
  props.workoutSets.map((set, index) => {
    const isRest = set.setType === 'rest'
    return {
      index: index + 1,
      setType: set.setType,
      duration: formatHmsDuration(set.duration),
      reps: isRest ? null : set.repetitions,
      exercise: isRest
        ? null
        : resolveExerciseName(props.exerciseTitles, set.categorySubtype, set.category),
      weight: isRest ? null : set.weight,
    }
  }),
)

const hasSteps = computed(() => stepRows.value.length > 0)
const hasSets = computed(() => setRows.value.length > 0)

// Each optional column is shown only when at least one row carries that value,
// so the table adapts to the activity (strength reps/weight, swim strokes,
// structured intervals) without per-activity-type rules.
const showStepType = computed(() => stepRows.value.some((row) => row.intensity !== null))
const showStepDuration = computed(() => stepRows.value.some((row) => row.duration !== null))
const showStepReps = computed(() => stepRows.value.some((row) => row.reps !== null))
const showStepExercise = computed(() => stepRows.value.some((row) => row.exercise !== null))
const showStepStroke = computed(() => stepRows.value.some((row) => row.stroke !== null))

const showSetReps = computed(() => setRows.value.some((row) => row.reps !== null))
const showSetExercise = computed(() => setRows.value.some((row) => row.exercise !== null))
const showSetWeight = computed(() => setRows.value.some((row) => row.weight !== null))
</script>

<template>
  <div class="flex flex-col gap-3">
    <!-- Planned steps (swim stroke / structured intervals). -->
    <div v-if="hasSteps">
      <h3 class="text-card-heading mb-2">{{ t('activities.workout.stepsTitle') }}</h3>
      <div class="overflow-x-auto">
        <table class="w-full min-w-[20rem] border-collapse text-meta">
          <thead>
            <tr class="text-caption border-b border-border text-left">
              <th class="py-2 pe-3 font-medium">{{ t('activities.workout.number') }}</th>
              <th v-if="showStepType" class="py-2 pe-3 font-medium">
                {{ t('activities.workout.type') }}
              </th>
              <th v-if="showStepDuration" class="py-2 pe-3 font-medium">
                {{ t('activities.workout.duration') }}
              </th>
              <th v-if="showStepReps" class="py-2 pe-3 font-medium">
                {{ t('activities.workout.reps') }}
              </th>
              <th v-if="showStepExercise" class="py-2 pe-3 font-medium">
                {{ t('activities.workout.exercise') }}
              </th>
              <th v-if="showStepStroke" class="py-2 pe-3 font-medium">
                {{ t('activities.workout.stroke') }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in stepRows"
              :key="row.index"
              class="border-b border-border/60 last:border-0"
            >
              <td class="py-2 pe-3 font-medium text-foreground">{{ row.index }}</td>
              <td v-if="showStepType" class="py-2 pe-3 capitalize text-muted-foreground">
                {{ row.intensity ?? '--' }}
              </td>
              <td v-if="showStepDuration" class="py-2 pe-3 text-foreground">
                {{ row.duration ?? '--' }}
              </td>
              <td v-if="showStepReps" class="py-2 pe-3 text-foreground">{{ row.reps ?? '--' }}</td>
              <td v-if="showStepExercise" class="py-2 pe-3 text-foreground">
                {{ row.exercise ?? '--' }}
              </td>
              <td v-if="showStepStroke" class="py-2 pe-3 capitalize text-muted-foreground">
                {{ row.stroke ?? '--' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Performed sets (reps, exercise & weight). -->
    <div v-if="hasSets">
      <h3 class="text-card-heading mb-2">{{ t('activities.workout.setsTitle') }}</h3>
      <div class="overflow-x-auto">
        <table class="w-full min-w-[20rem] border-collapse text-meta">
          <thead>
            <tr class="text-caption border-b border-border text-left">
              <th class="py-2 pe-3 font-medium">{{ t('activities.workout.number') }}</th>
              <th class="py-2 pe-3 font-medium">{{ t('activities.workout.type') }}</th>
              <th class="py-2 pe-3 font-medium">{{ t('activities.workout.duration') }}</th>
              <th v-if="showSetReps" class="py-2 pe-3 font-medium">
                {{ t('activities.workout.reps') }}
              </th>
              <th v-if="showSetExercise" class="py-2 pe-3 font-medium">
                {{ t('activities.workout.exercise') }}
              </th>
              <th v-if="showSetWeight" class="py-2 pe-3 font-medium">
                {{ t('activities.workout.weight') }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in setRows"
              :key="row.index"
              class="border-b border-border/60 last:border-0"
            >
              <td class="py-2 pe-3 font-medium text-foreground">{{ row.index }}</td>
              <td class="py-2 pe-3 capitalize text-muted-foreground">{{ row.setType }}</td>
              <td class="py-2 pe-3 text-foreground">{{ row.duration }}</td>
              <td v-if="showSetReps" class="py-2 pe-3 text-foreground">{{ row.reps ?? '--' }}</td>
              <td v-if="showSetExercise" class="py-2 pe-3 text-foreground">
                {{ row.exercise ?? '--' }}
              </td>
              <td v-if="showSetWeight" class="py-2 pe-3 text-muted-foreground">
                {{ row.weight ?? '--' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
