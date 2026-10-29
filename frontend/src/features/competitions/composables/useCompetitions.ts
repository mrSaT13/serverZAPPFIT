import { useQuery } from '@tanstack/vue-query'

import { fetchNextCompetition } from '@/features/competitions/services/competitions'
import { queryKeys } from '@/services/queryKeys'

/**
 * The user's next upcoming competition + training-readiness estimate, as
 * shown in the overview ("Обзор") widget. Rarely changes — a five-minute
 * staleness window keeps the dashboard cheap.
 */
export function useNextCompetitionQuery() {
  return useQuery({
    queryKey: queryKeys.competitions.next(),
    queryFn: fetchNextCompetition,
    staleTime: 5 * 60 * 1000,
  })
}
