import type { GearActivitiesPage, GearActivity, GearActivityDto } from '@/features/gears/types'
import type { Schemas } from '@/types'

import { apiFetch } from '@/services/http'

/** Pagination input for an activities-for-a-gear request. */
export interface GearActivitiesListParams {
  /** 1-based page number. */
  page: number
  /** Page size (records per page). */
  numRecords: number
}

/**
 * Maps a raw `Activity` payload to the trimmed {@link GearActivity} model used
 * by the read-only gear-detail list.
 *
 * @param dto - Raw activity payload from the backend.
 * @returns The normalized, trimmed activity model.
 */
export function mapGearActivity(dto: GearActivityDto): GearActivity {
  return {
    id: dto.id ?? 0,
    name: dto.name,
    activityType: dto.activity_type,
    startTime: dto.start_time ?? null,
    distance: dto.distance,
    totalTimerTime: dto.total_timer_time ?? null,
  }
}

/**
 * Fetches one page of the activities recorded against a gear.
 *
 * @param gearId - The parent gear id.
 * @param params - Page number and size.
 * @param signal - Optional abort signal so TanStack Query can cancel the
 *   request on unmount or invalidation.
 * @returns The page's activities (mapped) plus the total record count.
 * @throws {HttpError} When the request fails.
 */
export async function fetchGearActivities(
  gearId: number,
  { page, numRecords }: GearActivitiesListParams,
  signal?: AbortSignal,
): Promise<GearActivitiesPage> {
  const params = new URLSearchParams({
    page_number: String(page),
    num_records: String(numRecords),
  })
  const response = await apiFetch<Schemas['GearActivitiesListResponse']>(
    `/activities/gear/${gearId}/list?${params.toString()}`,
    { signal },
  )
  return {
    records: (response.records ?? []).map(mapGearActivity),
    total: response.total,
  }
}
