/**
 * TanStack Query composable for the activity summary. Wraps
 * {@link fetchActivitySummary} behind the centralized `activities.summary` key
 * so a broad activities invalidation (after an upload or delete) also refreshes
 * the summary. Keeps the previous period's data on screen while the next loads,
 * avoiding a flash of empty totals when navigating periods or switching views.
 */

import { computed, type MaybeRefOrGetter, toValue } from 'vue'
import { storeToRefs } from 'pinia'
import { keepPreviousData, useQuery } from '@tanstack/vue-query'

import type { ActivitySummaryParams } from '@/features/summary/services/summary'
import type { SummaryViewType } from '@/features/summary/types'

import { queryKeys } from '@/services/queryKeys'
import { useAuthStore } from '@/features/auth/stores/auth'
import { fetchActivitySummary } from '@/features/summary/services/summary'

/**
 * The authenticated user's aggregated activity summary for a view type, period,
 * and optional type filter. Keyed on every input so each distinct query caches
 * independently; gated on authentication.
 *
 * @param viewType - Reactive period granularity (`week`/`month`/`year`/`lifetime`).
 * @param params - Reactive date/year anchor and optional type-name filter.
 * @returns The TanStack query result for the current summary.
 */
export function useActivitySummaryQuery(
  viewType: MaybeRefOrGetter<SummaryViewType>,
  params: MaybeRefOrGetter<ActivitySummaryParams>,
) {
  const { isAuthenticated } = storeToRefs(useAuthStore())

  return useQuery({
    queryKey: computed(() =>
      queryKeys.activities.summary({ viewType: toValue(viewType), ...toValue(params) }),
    ),
    queryFn: ({ signal }) => fetchActivitySummary(toValue(viewType), toValue(params), signal),
    placeholderData: keepPreviousData,
    enabled: isAuthenticated,
  })
}
