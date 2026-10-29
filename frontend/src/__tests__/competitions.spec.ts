import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiFetch } from '@/services/http'
import { fetchNextCompetition } from '@/features/competitions/services/competitions'

vi.mock('@/services/http', () => ({
  apiFetch: vi.fn<typeof apiFetch>(),
}))

describe('competitions service requests', () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset()
  })

  it('fetchNextCompetition hits /competitions/next and maps the readiness snapshot', async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      competition: {
        id: 5,
        user_id: 1,
        name: 'Городской полумарафон',
        competition_date: '2026-11-22',
        distance_km: 21.1,
        note: 'порог 1:45',
        status: 'upcoming',
        place: null,
        total_participants: null,
        result_time_s: null,
      },
      days_left: 28,
      avg_weekly_km: 33.5,
      required_weekly_km: 45,
      readiness: 0.74,
    })

    const snap = await fetchNextCompetition()

    expect(apiFetch).toHaveBeenCalledWith('/competitions/next')
    expect(snap.competition?.name).toBe('Городской полумарафон')
    expect(snap.days_left).toBe(28)
    expect(snap.readiness).toBe(0.74)
  })

  it('fetchNextCompetition passes the empty snapshot through untouched', async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      competition: null,
      days_left: 0,
      avg_weekly_km: 0,
      required_weekly_km: 0,
      readiness: 0,
    })

    const snap = await fetchNextCompetition()

    expect(snap.competition).toBeNull()
    expect(snap.readiness).toBe(0)
  })
})
