import { apiFetch } from '@/services/http'

export interface TrainingMetrics {
  ctl: number
  atl: number
  tsb: number
  tssToday: number
  points: Array<{ date: string; tss: number }>
}

interface PmcResponse {
  ctl: number
  atl: number
  tsb: number
  tss_today: number
  points: Array<{ date: string; tss: number }>
}

export async function fetchTrainingMetrics(): Promise<TrainingMetrics> {
  const res = await apiFetch<PmcResponse>('/activities/pmc?days=90')
  return {
    ctl: Number(res.ctl ?? 0),
    atl: Number(res.atl ?? 0),
    tsb: Number(res.tsb ?? 0),
    tssToday: Number(res.tss_today ?? 0),
    points: Array.isArray(res.points) ? res.points : [],
  }
}

export function formLabel(tsb: number) {
  if (tsb > 25) return { label: 'Пик', color: 'text-blue-600' }
  if (tsb > 5) return { label: 'Свеж', color: 'text-green-600' }
  if (tsb > -10) return { label: 'Нейтрально', color: 'text-yellow-600' }
  if (tsb > -30) return { label: 'Утомлен', color: 'text-orange-600' }
  return { label: 'Перетрен', color: 'text-red-600' }
}
