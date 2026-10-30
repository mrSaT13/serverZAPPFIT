import { apiFetch } from '@/services/http'

export interface MealLog {
  id: number
  user_id: number
  date: string
  meal_type: 'breakfast' | 'lunch' | 'dinner' | 'snack'
  product_name: string
  calories: number | null
  protein: number | null
  carbs: number | null
  fat: number | null
  portion_g: number | null
  off_barcode: string | null
  created_at: string | null
}

export interface OffProduct {
  barcode: string | null
  product_name: string | null
  brands: string | null
  calories_100g: number | null
  proteins_100g: number | null
  carbs_100g: number | null
  fat_100g: number | null
  image_url: string | null
}

export interface FoodFavorite {
  product_name: string
  calories: number | null
  protein: number | null
  carbs: number | null
  fat: number | null
  portion_g: number | null
  off_barcode: string | null
  last_logged: string | null
  times_logged: number
}

export async function fetchLogs(date?: string): Promise<MealLog[]> {
  const qs = date ? `?date_from=${date}&date_to=${date}` : ''
  return apiFetch<MealLog[]>(`/nutrition${qs}`)
}

export async function createLog(
  payload: Omit<MealLog, 'id' | 'user_id' | 'created_at'>,
): Promise<MealLog> {
  return apiFetch<MealLog>(`/nutrition`, { method: 'POST', body: JSON.stringify(payload) })
}

export async function deleteLog(id: number): Promise<void> {
  await apiFetch(`/nutrition/${id}`, { method: 'DELETE', responseType: 'void' })
}

export async function searchOff(q: string, language?: string): Promise<OffProduct[]> {
  const qs = new URLSearchParams({ q })
  if (language) qs.set('language', language)
  return apiFetch<OffProduct[]>(`/nutrition/off/search?${qs.toString()}`)
}

export async function getOffProduct(barcode: string): Promise<OffProduct> {
  return apiFetch<OffProduct>(`/nutrition/off/product/${barcode}`)
}

/** Repeat-food suggestions from the user's own log history. */
export async function fetchFavorites(query: string, limit = 6): Promise<FoodFavorite[]> {
  const qs = new URLSearchParams({ query, limit: String(limit) })
  return apiFetch<FoodFavorite[]>(`/nutrition/favorites?${qs.toString()}`)
}

export async function fetchSummary(date: string) {
  return apiFetch<{
    date: string
    intake_calories: number
    intake_protein: number
    intake_carbs: number
    intake_fat: number
    burned_calories: number | null
    net_calories: number | null
  }>(`/nutrition/summary?date=${date}`)
}

export interface NutritionTrendPoint {
  date: string
  calories: number
  protein: number
  carbs: number
  fat: number
  burned_calories: number | null
}

export interface NutritionTrend {
  date_from: string
  date_to: string
  days: NutritionTrendPoint[]
}

/** Per-day intake (+ burned) totals for the nutrition page charts. */
export async function fetchTrend(dateFrom: string, dateTo: string): Promise<NutritionTrend> {
  const qs = new URLSearchParams({ date_from: dateFrom, date_to: dateTo })
  return apiFetch<NutritionTrend>(`/nutrition/trend?${qs.toString()}`)
}

export interface AiChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface AiStatus {
  enabled: boolean
  configured: boolean
  model: string | null
}

export interface AiChatReply {
  reply: string
  model: string | null
}

/** Whether the AI nutrition assistant is available for this server. */
export async function fetchAiStatus(): Promise<AiStatus> {
  return apiFetch<AiStatus>(`/nutrition/ai/status`)
}

/**
 * Sends the recent chat window plus a language hint; the server rebuilds the
 * read-only data snapshot on every call (stateless multi-turn chat).
 */
export async function aiChat(messages: AiChatMessage[], language: string): Promise<AiChatReply> {
  return apiFetch<AiChatReply>(`/nutrition/ai/chat`, {
    method: 'POST',
    body: JSON.stringify({ messages, language }),
  })
}
