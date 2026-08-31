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

export async function fetchLogs(date?: string): Promise<MealLog[]> {
  const qs = date ? `?date_from=${date}&date_to=${date}` : ''
  return apiFetch<MealLog[]>(`/nutrition${qs}`)
}

export async function createLog(payload: Omit<MealLog, 'id' | 'user_id' | 'created_at'>): Promise<MealLog> {
  return apiFetch<MealLog>(`/nutrition`, { method: 'POST', body: JSON.stringify(payload) })
}

export async function deleteLog(id: number): Promise<void> {
  await apiFetch(`/nutrition/${id}`, { method: 'DELETE', responseType: 'void' })
}

export async function searchOff(q: string): Promise<OffProduct[]> {
  return apiFetch<OffProduct[]>(`/nutrition/off/search?q=${encodeURIComponent(q)}`)
}

export async function getOffProduct(barcode: string): Promise<OffProduct> {
  return apiFetch<OffProduct>(`/nutrition/off/product/${barcode}`)
}

export async function fetchSummary(date: string) {
  return apiFetch<{ date: string; intake_calories: number; intake_protein: number; intake_carbs: number; intake_fat: number; burned_calories: number | null; net_calories: number | null }>(`/nutrition/summary?date=${date}`)
}
