<!-- Strength workouts page: plans, session history and exercise progress. -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Dumbbell, History, Plus, TrendingUp, Upload } from '@lucide/vue'
import { useQuery } from '@tanstack/vue-query'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { EmptyState } from '@/components/ui/empty-state'
import { Skeleton } from '@/components/ui/skeleton'
import PlanDialog, {
  type PlanDialogSavePayload,
} from '@/features/strength/components/PlanDialog.vue'
import SessionDialog from '@/features/strength/components/SessionDialog.vue'
import ImportWgerDialog from '@/features/strength/components/ImportWgerDialog.vue'
import WorkoutWeeklyChart from '@/features/strength/components/WorkoutWeeklyChart.vue'
import ExerciseProgressChart from '@/features/strength/components/ExerciseProgressChart.vue'
import {
  createPlan,
  deletePlan,
  deleteSession,
  fetchPlans,
  fetchProgress,
  fetchSessions,
  fetchWorkoutStatistics,
  updatePlan,
  type WorkoutPlan,
} from '@/features/strength/services/workouts'
import { useToasts } from '@/composables/useToasts'
import { queryKeys } from '@/services/queryKeys'

const { t } = useI18n()
const toasts = useToasts()

const section = ref<'plans' | 'history' | 'charts' | 'progress'>('plans')
const planDialogOpen = ref(false)
const editingPlan = ref<WorkoutPlan | null>(null)
const sessionDialogOpen = ref(false)
const importDialogOpen = ref(false)
const sessionTarget = ref<WorkoutPlan | null>(null)
const deleteTarget = ref<WorkoutPlan | { kind: 'session'; id: number } | null>(null)
const isDeleteOpen = ref(false)

const plansQuery = useQuery({ queryKey: queryKeys.workouts.plans(), queryFn: fetchPlans })
const sessionsQuery = useQuery({
  queryKey: queryKeys.workouts.sessions(),
  queryFn: () => fetchSessions(),
})
const progressQuery = useQuery({ queryKey: queryKeys.workouts.progress(), queryFn: fetchProgress })
const statisticsQuery = useQuery({
  queryKey: queryKeys.workouts.statistics(),
  queryFn: () => fetchWorkoutStatistics(),
})

const plans = computed(() => plansQuery.data.value ?? [])
const sessions = computed(() => sessionsQuery.data.value ?? [])
const progress = computed(() => progressQuery.data.value ?? [])
const statistics = computed(() => statisticsQuery.data.value ?? null)

function invalidate(): void {
  void plansQuery.refetch()
  void sessionsQuery.refetch()
  void progressQuery.refetch()
  void statisticsQuery.refetch()
}

function askDelete(target: WorkoutPlan | { kind: 'session'; id: number }): void {
  deleteTarget.value = target
  isDeleteOpen.value = true
}

async function doDelete(): Promise<void> {
  const target = deleteTarget.value
  deleteTarget.value = null
  isDeleteOpen.value = false
  if (!target) return
  try {
    if ('kind' in target) {
      await deleteSession(target.id)
    } else {
      await deletePlan(target.id)
    }
    toasts.success(t('workouts.deleted'))
    invalidate()
  } catch (e: unknown) {
    toasts.error((e as Error)?.message || t('app.error.toast'))
  }
}

async function savePlan(payload: PlanDialogSavePayload): Promise<void> {
  if (!payload?.name?.trim()) return
  try {
    if (editingPlan.value) await updatePlan(editingPlan.value.id, payload)
    else await createPlan(payload)
    toasts.success(t('workouts.plan.saved'))
    editingPlan.value = null
    invalidate()
  } catch (e: unknown) {
    toasts.error((e as Error)?.message || t('app.error.toast'))
  }
}

function openSession(plan: WorkoutPlan | null): void {
  sessionTarget.value = plan
  sessionDialogOpen.value = true
}

function editPlan(plan: WorkoutPlan): void {
  editingPlan.value = plan
  planDialogOpen.value = true
}

function newPlan(): void {
  editingPlan.value = null
  planDialogOpen.value = true
}

watch(sessionDialogOpen, (v) => {
  if (!v) sessionTarget.value = null
})

/** Distinct day labels of a plan, in first-appearance order. */
function planDays(plan: WorkoutPlan): string[] {
  const out: string[] = []
  for (const ex of plan.exercises) {
    const label = ex.day_label ?? ''
    if (!out.includes(label)) out.push(label)
  }
  return out.slice(0, 6)
}
</script>

<template>
  <section class="flex flex-col gap-3">
    <!-- heading -->
    <div class="flex flex-wrap items-center gap-2">
      <Dumbbell class="size-6" />
      <h1 class="text-page-title">{{ t('workouts.title') }}</h1>
      <span class="text-body text-muted-foreground">{{ t('workouts.subtitle') }}</span>
      <div class="ml-auto flex flex-wrap gap-2">
        <Button variant="outline" @click="importDialogOpen = true">
          <Upload class="size-4" /> {{ t('workouts.import.title') }}
        </Button>
        <Button variant="outline" @click="newPlan">
          <Plus class="size-4" /> {{ t('workouts.plan.createTitle') }}
        </Button>
        <Button @click="openSession(null)">
          <History class="size-4" /> {{ t('workouts.session.logEmpty') }}
        </Button>
      </div>
    </div>

    <!-- section switch -->
    <div class="flex gap-2 overflow-x-auto pb-1">
      <Button
        v-for="s in ['plans', 'history', 'charts', 'progress'] as const"
        :key="s"
        size="sm"
        class="shrink-0"
        :variant="section === s ? 'secondary' : 'ghost'"
        @click="section = s"
      >
        <History v-if="s === 'history'" class="size-4" />
        <TrendingUp v-else-if="s === 'progress'" class="size-4" />
        <Dumbbell v-else class="size-4" />
        {{ t(`workouts.sections.${s}`) }}
      </Button>
    </div>

    <!-- PLANS -->
    <template v-if="section === 'plans'">
      <div v-if="plansQuery.isPending.value" class="flex flex-col gap-2">
        <Skeleton v-for="i in 3" :key="i" class="h-20 w-full" />
      </div>
      <div v-else class="grid gap-3 md:grid-cols-2">
        <Card v-for="plan in plans" :key="plan.id" class="flex min-w-0 flex-col gap-2 p-4">
          <div class="flex min-w-0 flex-wrap items-start gap-2">
            <div class="flex min-w-0 flex-1 flex-col">
              <span class="truncate font-medium">{{ plan.name }}</span>
              <span class="text-hint">
                {{ plan.source === 'wger' ? t('workouts.fromWger') : t('workouts.manual') }}
                · {{ plan.exercises.length }} {{ t('workouts.exercisesShort') }}
              </span>
            </div>
            <div class="flex flex-wrap gap-1">
              <Button size="sm" variant="secondary" @click="openSession(plan)">
                {{ t('workouts.session.start') }}
              </Button>
              <Button size="sm" variant="outline" @click="editPlan(plan)">
                {{ t('workouts.edit') }}
              </Button>
              <Button size="sm" variant="ghost" class="text-destructive" @click="askDelete(plan)">
                {{ t('workouts.delete') }}
              </Button>
            </div>
          </div>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="day in planDays(plan)"
              :key="day"
              class="rounded-full bg-muted px-2 py-0.5 text-hint"
            >
              {{ day || t('workouts.plan.ungrouped') }}
              ·
              {{ plan.exercises.filter((e) => (e.day_label ?? '') === day).length }}
            </span>
          </div>
        </Card>
        <EmptyState
          v-if="!plansQuery.isPending.value && plans.length === 0"
          class="md:col-span-2"
          :title="t('workouts.plansEmpty.title')"
          :description="t('workouts.plansEmpty.description')"
        />
      </div>
    </template>

    <!-- HISTORY -->
    <template v-else-if="section === 'history'">
      <div v-if="sessionsQuery.isPending.value" class="flex flex-col gap-2">
        <Skeleton v-for="i in 3" :key="i" class="h-14 w-full" />
      </div>
      <Card v-else-if="sessions.length" class="flex flex-col gap-1">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="flex items-center gap-2 rounded-input border px-3 py-2"
        >
          <div class="flex min-w-0 flex-col">
            <span class="text-body font-medium">{{ s.date }}</span>
            <span class="text-hint truncate">
              {{ s.sets.length }} {{ t('workouts.setsShort') }}
              <template v-if="s.duration_min">
                · {{ s.duration_min }} {{ t('workouts.minutesShort') }}</template
              >
              {{ s.comment ? ' · ' + s.comment : '' }}
            </span>
          </div>
          <Button
            class="ml-auto"
            size="sm"
            variant="ghost"
            @click="askDelete({ kind: 'session', id: s.id })"
          >
            {{ t('workouts.delete') }}
          </Button>
        </div>
      </Card>
      <EmptyState
        v-else
        :title="t('workouts.historyEmpty.title')"
        :description="t('workouts.historyEmpty.description')"
      />
    </template>

    <!-- CHARTS -->
    <template v-else-if="section === 'charts'">
      <div v-if="statisticsQuery.isPending.value" class="flex flex-col gap-2">
        <Skeleton v-for="i in 2" :key="i" class="h-64 w-full" />
      </div>
      <div v-else-if="(statistics?.weeks.length ?? 0) > 0" class="flex flex-col gap-3">
        <WorkoutWeeklyChart :weeks="statistics!.weeks" metric="volume" />
        <WorkoutWeeklyChart :weeks="statistics!.weeks" metric="sessions" />
        <ExerciseProgressChart :progress="progress" />
      </div>
      <EmptyState
        v-else
        :title="t('workouts.charts.empty.title')"
        :description="t('workouts.charts.empty.description')"
      />
    </template>

    <!-- PROGRESS -->
    <template v-else>
      <div v-if="progressQuery.isPending.value" class="flex flex-col gap-2">
        <Skeleton v-for="i in 3" :key="i" class="h-14 w-full" />
      </div>
      <Card v-else-if="progress.length" class="flex flex-col gap-1">
        <div v-for="p in progress" :key="p.exercise_name" class="rounded-input border px-3 py-2">
          <div class="flex items-center justify-between gap-2">
            <span class="truncate text-body font-medium">{{ p.exercise_name }}</span>
            <span class="text-hint whitespace-nowrap">
              {{ p.sessions }} {{ t('workouts.sessionsShort') }}
              <template v-if="p.best_est_1rm">
                · 1RM ≈ {{ (Math.round(p.best_est_1rm * 10) / 10).toFixed(1) }}
                {{ t('workouts.kg') }}</template
              >
            </span>
          </div>
          <template v-if="p.points.length">
            <div class="text-hint mt-0.5">
              {{ p.points[p.points.length - 1]?.date }}
              —
              {{
                (
                  Math.round((p.points[p.points.length - 1]?.best_weight_kg ?? 0) * 10) / 10
                ).toFixed(1)
              }}
              {{ t('workouts.kg') }} × {{ p.points[p.points.length - 1]?.best_reps ?? 0 }}
            </div>
          </template>
        </div>
      </Card>
      <EmptyState
        v-else
        :title="t('workouts.progressEmpty.title')"
        :description="t('workouts.progressEmpty.description')"
      />
    </template>

    <PlanDialog v-model:open="planDialogOpen" :plan="editingPlan" @saved="savePlan" />
    <SessionDialog v-model:open="sessionDialogOpen" :plan="sessionTarget" @saved="invalidate" />
    <ImportWgerDialog v-model:open="importDialogOpen" @imported="invalidate" />

    <ConfirmDialog
      v-model:open="isDeleteOpen"
      :title="t('workouts.deleteConfirm.title')"
      :description="t('workouts.deleteConfirm.description')"
      :confirm-label="t('workouts.delete')"
      :cancel-label="t('workouts.form.cancel')"
      :close-label="t('workouts.form.cancel')"
      @confirm="doDelete"
    />
  </section>
</template>
