/**
 * Strength-workout API client. Mirrors the backend `workouts` router
 * (paths relative to the API base). Types are local — regenerate
 * `api.generated.ts` after the next OpenAPI export to fold them into the
 * generated client namespace.
 */

import { apiFetch } from '@/services/http'

export type PlanSource = 'manual' | 'wger'

export interface PlanExercise {
  position: number
  day_label?: string | null
  name: string
  muscle_group?: string | null
  wger_exercise_id?: number | null
  notes?: string | null
  target_sets?: number | null
  target_reps?: string | null
  target_weight_kg?: number | null
  rest_s?: number | null
}

export interface PlanExerciseRead extends PlanExercise {
  id: number
}

export interface WorkoutPlan {
  id: number
  user_id: number
  name: string
  description?: string | null
  source: PlanSource
  wger_plan_id?: number | null
  created_at?: string | null
  updated_at?: string | null
  exercises: PlanExerciseRead[]
}

export interface SetLog {
  exercise_name: string
  wger_exercise_id?: number | null
  set_no: number
  weight_kg?: number | null
  reps?: number | null
  rpe?: number | null
  completed?: boolean
}

export interface WorkoutSession {
  id: number
  user_id: number
  plan_id?: number | null
  date: string
  duration_min?: number | null
  calories?: number | null
  comment?: string | null
  created_at?: string | null
  sets: Array<SetLog & { id: number; session_id: number }>
}

export interface ExercisePoint {
  date: string
  best_weight_kg?: number | null
  best_reps?: number | null
  est_1rm?: number | null
  total_volume: number
}

export interface ExerciseProgress {
  exercise_name: string
  wger_exercise_id?: number | null
  sessions: number
  best_weight_kg?: number | null
  best_est_1rm?: number | null
  points: ExercisePoint[]
}

export interface WorkoutStatisticsPoint {
  week_start: string
  sessions: number
  volume_kg: number
  sets: number
  reps: number
}

export interface WorkoutStatistics {
  date_from: string
  date_to: string
  total_sessions: number
  total_volume_kg: number
  total_sets: number
  total_reps: number
  weeks: WorkoutStatisticsPoint[]
}

export interface AiPlanStatus {
  enabled: boolean
  configured: boolean
  model: string | null
}

export interface AiPlanDraft {
  name: string
  description?: string | null
  exercises: PlanExercise[]
  model?: string | null
}

export interface CatalogTranslation {
  name: string
  description: string
}

export interface CatalogExercise {
  wger_id: number
  uuid: string
  name: string
  translations: Record<string, CatalogTranslation>
  category?: { id: number; name: string } | null
  muscles: Array<{ id: number; name: string; name_en: string; is_front: boolean }>
  muscles_secondary: Array<{ id: number; name: string; name_en: string; is_front: boolean }>
  equipment: Array<{ id: number; name: string }>
  variation_group?: string | null
  license_author?: string | null
  /** Full CC license name harvested from wger (e.g. "Creative Commons Attribution Share Alike 4"). */
  license?: string | null
  /** Alternative exercise names per language — search synonyms. */
  aliases?: Record<string, string[]>
  /** Short technique tips per language (wger exercise comments). */
  tips?: Record<string, string[]>
}

export interface CatalogMeta {
  counts: { exercises: number; seedError?: number }
  categories: Array<{ id: number; name: string }>
  equipment: Array<{ id: number; name: string }>
  muscles: Array<{ id: number; name: string; name_en: string; is_front: boolean }>
}

export interface WgerRoutinePreview {
  wger_id: number
  name?: string | null
  start?: string | null
  end?: string | null
  days: number
  is_template: boolean
}

// ---- plans ----

export function fetchPlans(): Promise<WorkoutPlan[]> {
  return apiFetch<WorkoutPlan[]>('/workouts')
}

export function createPlan(body: {
  name: string
  description?: string | null
  exercises: PlanExercise[]
}): Promise<WorkoutPlan> {
  return apiFetch<WorkoutPlan>('/workouts', { method: 'POST', body: JSON.stringify(body) })
}

export function updatePlan(
  id: number,
  body: { name: string; description?: string | null; exercises: PlanExercise[] },
): Promise<WorkoutPlan> {
  return apiFetch<WorkoutPlan>(`/workouts/${id}`, { method: 'PUT', body: JSON.stringify(body) })
}

export async function deletePlan(id: number): Promise<void> {
  await apiFetch<void>(`/workouts/${id}`, { method: 'DELETE', responseType: 'void' })
}

// ---- sessions ----

export function fetchSessions(dateFrom?: string, dateTo?: string): Promise<WorkoutSession[]> {
  const qs = new URLSearchParams()
  if (dateFrom) qs.set('date_from', dateFrom)
  if (dateTo) qs.set('date_to', dateTo)
  const q = qs.size ? `?${qs}` : ''
  return apiFetch<WorkoutSession[]>(`/workouts/sessions${q}`)
}

export function createSession(body: {
  date: string
  plan_id?: number | null
  duration_min?: number | null
  calories?: number | null
  comment?: string | null
  sets: SetLog[]
}): Promise<WorkoutSession> {
  return apiFetch<WorkoutSession>('/workouts/sessions', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function deleteSession(id: number): Promise<void> {
  await apiFetch<void>(`/workouts/sessions/${id}`, { method: 'DELETE', responseType: 'void' })
}

// ---- progress ----

export function fetchProgress(): Promise<ExerciseProgress[]> {
  return apiFetch<ExerciseProgress[]>('/workouts/progress')
}

// ---- statistics ----

export function fetchWorkoutStatistics(
  dateFrom?: string,
  dateTo?: string,
): Promise<WorkoutStatistics> {
  const qs = new URLSearchParams()
  if (dateFrom) qs.set('date_from', dateFrom)
  if (dateTo) qs.set('date_to', dateTo)
  const q = qs.size ? `?${qs}` : ''
  return apiFetch<WorkoutStatistics>(`/workouts/statistics${q}`)
}

// ---- AI plan generator ----

export function fetchAiPlanStatus(): Promise<AiPlanStatus> {
  return apiFetch<AiPlanStatus>('/workouts/ai/status')
}

export function generateAiPlan(prompt: string, language?: string): Promise<AiPlanDraft> {
  return apiFetch<AiPlanDraft>('/workouts/ai/plan', {
    method: 'POST',
    body: JSON.stringify({ prompt, language: language ?? null }),
  })
}

// ---- catalog ----

export function searchCatalog(
  q?: string,
  extra?: { category_id?: number; equipment_id?: number; muscle_id?: number; lang?: string },
): Promise<{ total: number; records: CatalogExercise[] }> {
  const qs = new URLSearchParams()
  if (q?.trim()) qs.set('q', q.trim())
  if (extra?.category_id != null) qs.set('category_id', String(extra.category_id))
  if (extra?.equipment_id != null) qs.set('equipment_id', String(extra.equipment_id))
  if (extra?.muscle_id != null) qs.set('muscle_id', String(extra.muscle_id))
  if (extra?.lang) qs.set('lang', extra.lang)
  qs.set('limit', '50')
  return apiFetch<{ total: number; records: CatalogExercise[] }>(`/workouts/exercises?${qs}`)
}

export function fetchCatalogMeta(): Promise<CatalogMeta> {
  return apiFetch<CatalogMeta>('/workouts/exercises/meta')
}

// ---- wger import ----

export function previewWgerRoutines(): Promise<WgerRoutinePreview[]> {
  return apiFetch<WgerRoutinePreview[]>('/workouts/import/wger')
}

export function importWgerRoutine(wgerId: number): Promise<WorkoutPlan> {
  return apiFetch<WorkoutPlan>(`/workouts/import/wger/${wgerId}`, { method: 'POST' })
}
