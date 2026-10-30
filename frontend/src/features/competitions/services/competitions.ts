import { apiFetch } from '@/services/http'

/** Server-side competition record (mirror of the mobile client's local one). */
export interface Competition {
  id: number
  user_id: number
  name: string
  /** Race day, ISO `YYYY-MM-DD` (time stayed on the client side). */
  competition_date: string
  /** Declared race distance in kilometres. */
  distance_km: number
  note: string | null
  status: 'upcoming' | 'completed'
  place: number | null
  total_participants: number | null
  result_time_s: number | null
}

/** `GET /competitions/next` response: the race widget's entire data model. */
export interface NextCompetition {
  competition: Competition | null
  days_left: number
  /** Rolling 28-day average weekly distance (all logged activities, km). */
  avg_weekly_km: number
  /** Weekly distance a race of this length expects. */
  required_weekly_km: number
  /** `avg / required`, clamped to [0, 1] — the progress-bar fraction. */
  readiness: number
}

/** The authenticated user's next upcoming race + readiness estimate. */
export function fetchNextCompetition(): Promise<NextCompetition> {
  return apiFetch<NextCompetition>('/competitions/next')
}

/** All of the user's competitions, newest race day first (calendar flags). */
export function fetchCompetitions(): Promise<Competition[]> {
  return apiFetch<Competition[]>('/competitions')
}
