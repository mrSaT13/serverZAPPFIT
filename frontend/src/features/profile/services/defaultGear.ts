import type { DefaultGear, DefaultGearDto, DefaultGearUpdateDto } from '@/features/profile/types'

import { apiFetch } from '@/services/http'

/**
 * Maps a raw default-gear payload to the clean {@link DefaultGear} model — the
 * single boundary where the backend wire format (snake_case) is normalized.
 *
 * @param dto - Raw default-gear payload from the backend.
 * @returns The normalized default-gear model.
 */
export function mapDefaultGear(dto: DefaultGearDto): DefaultGear {
  return {
    id: dto.id,
    userId: dto.user_id,
    runGearId: dto.run_gear_id ?? null,
    trailRunGearId: dto.trail_run_gear_id ?? null,
    virtualRunGearId: dto.virtual_run_gear_id ?? null,
    walkGearId: dto.walk_gear_id ?? null,
    hikeGearId: dto.hike_gear_id ?? null,
    rideGearId: dto.ride_gear_id ?? null,
    mtbRideGearId: dto.mtb_ride_gear_id ?? null,
    gravelRideGearId: dto.gravel_ride_gear_id ?? null,
    virtualRideGearId: dto.virtual_ride_gear_id ?? null,
    owsGearId: dto.ows_gear_id ?? null,
    tennisGearId: dto.tennis_gear_id ?? null,
    alpineSkiGearId: dto.alpine_ski_gear_id ?? null,
    nordicSkiGearId: dto.nordic_ski_gear_id ?? null,
    snowboardGearId: dto.snowboard_gear_id ?? null,
    windsurfGearId: dto.windsurf_gear_id ?? null,
  }
}

/**
 * Rebuilds the full update wire payload from a {@link DefaultGear}. The id and
 * user id round-trip so the backend (which forbids extra fields and replaces
 * the record) keeps ownership intact.
 *
 * @param gear - The default gear (already merged with any edits).
 * @returns The snake-cased update body.
 */
export function toDefaultGearWire(gear: DefaultGear): DefaultGearUpdateDto {
  return {
    id: gear.id,
    user_id: gear.userId,
    run_gear_id: gear.runGearId,
    trail_run_gear_id: gear.trailRunGearId,
    virtual_run_gear_id: gear.virtualRunGearId,
    walk_gear_id: gear.walkGearId,
    hike_gear_id: gear.hikeGearId,
    ride_gear_id: gear.rideGearId,
    mtb_ride_gear_id: gear.mtbRideGearId,
    gravel_ride_gear_id: gear.gravelRideGearId,
    virtual_ride_gear_id: gear.virtualRideGearId,
    ows_gear_id: gear.owsGearId,
    tennis_gear_id: gear.tennisGearId,
    alpine_ski_gear_id: gear.alpineSkiGearId,
    nordic_ski_gear_id: gear.nordicSkiGearId,
    snowboard_gear_id: gear.snowboardGearId,
    windsurf_gear_id: gear.windsurfGearId,
  }
}

/**
 * Fetches the authenticated user's default-gear assignments.
 *
 * @param signal - Optional abort signal for cancellation.
 * @returns The default gear, or `null` when no record exists yet.
 * @throws {HttpError} When the request fails.
 */
export async function fetchDefaultGear(signal?: AbortSignal): Promise<DefaultGear | null> {
  const dto = await apiFetch<DefaultGearDto | null>('/profile/default_gear', { signal })
  return dto ? mapDefaultGear(dto) : null
}

/**
 * Updates the authenticated user's default-gear assignments.
 *
 * @param gear - The full default-gear record to persist (with edits merged).
 * @returns The updated default gear, mapped to the clean model.
 * @throws {HttpError} When the request fails.
 */
export async function updateDefaultGear(gear: DefaultGear): Promise<DefaultGear> {
  const dto = await apiFetch<DefaultGearDto>('/profile/default_gear', {
    method: 'PUT',
    body: JSON.stringify(toDefaultGearWire(gear)),
  })
  return mapDefaultGear(dto)
}
