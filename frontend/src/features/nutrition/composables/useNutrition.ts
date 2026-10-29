import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'

import { fetchSummary } from '@/features/nutrition/services/nutrition'
import { queryKeys } from '@/services/queryKeys'

/**
 * Daily nutrition summary (intake/burned/net calories + macros) for the
 * health dashboard widgets. Keyed by date so the nutrition page and the
 * overview share one cache entry per day.
 *
 * @param date - Reactive ISO date (`YYYY-MM-DD`), e.g. a computed getter.
 * @returns TanStack query for the nutrition summary.
 */
export function useNutritionSummaryQuery(date: () => string) {
  return useQuery({
    queryKey: computed(() => queryKeys.nutrition.summary(date())),
    queryFn: () => fetchSummary(date()),
  })
}
