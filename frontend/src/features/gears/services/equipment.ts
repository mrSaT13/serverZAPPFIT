import { apiFetch } from '@/services/http'

/**
 * A piece of the user's training inventory (dumbbells, barbells, machines…).
 * Mirrors the backend `UserEquipment` wire shape.
 */
export interface EquipmentItem {
  id: number
  user_id: number
  /** Free-form display name, e.g. "Гантели 10 кг". */
  name: string
  /** Catalog equipment dictionary id (Barbell=1, Dumbbell=3, …), or null. */
  equipment_id: number | null
  /** Weight per item in kg, or null. */
  weight_kg: string | number | null
  quantity: number
}

export type EquipmentInput = Omit<EquipmentItem, 'id' | 'user_id'>

export function fetchEquipment(): Promise<EquipmentItem[]> {
  return apiFetch<EquipmentItem[]>('/workouts/equipment')
}

export function createEquipment(body: EquipmentInput): Promise<EquipmentItem> {
  return apiFetch<EquipmentItem>('/workouts/equipment', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function updateEquipment(id: number, body: EquipmentInput): Promise<EquipmentItem> {
  return apiFetch<EquipmentItem>(`/workouts/equipment/${id}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteEquipment(id: number): Promise<void> {
  await apiFetch<void>(`/workouts/equipment/${id}`, { method: 'DELETE', responseType: 'void' })
}
