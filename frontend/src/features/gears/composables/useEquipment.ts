import { useQuery } from '@tanstack/vue-query'

import type { EquipmentInput, EquipmentItem } from '@/features/gears/services/equipment'

import { useInvalidatingMutation } from '@/composables/useInvalidatingMutation'
import { queryKeys } from '@/services/queryKeys'
import {
  createEquipment,
  deleteEquipment,
  fetchEquipment,
  updateEquipment,
} from '@/features/gears/services/equipment'

/**
 * The authenticated user's training inventory (dumbbells/barbells/… with
 * weights) powering the AI planner's feasibility filter.
 *
 * @returns The TanStack query result for the inventory list.
 */
export function useEquipmentQuery() {
  return useQuery<EquipmentItem[]>({
    queryKey: queryKeys.workouts.equipment(),
    queryFn: () => fetchEquipment(),
  })
}

/** Create mutation; invalidates the inventory list on settle. */
export function useCreateEquipmentMutation() {
  return useInvalidatingMutation<EquipmentItem, EquipmentInput>({
    mutationKey: queryKeys.workouts.equipment(),
    mutationFn: (input) => createEquipment(input),
  })
}

/** Update mutation; invalidates the inventory list on settle. */
export function useUpdateEquipmentMutation() {
  return useInvalidatingMutation<EquipmentItem, { id: number; input: EquipmentInput }>({
    mutationKey: queryKeys.workouts.equipment(),
    mutationFn: ({ id, input }) => updateEquipment(id, input),
  })
}

/** Delete mutation; invalidates the inventory list on settle. */
export function useDeleteEquipmentMutation() {
  return useInvalidatingMutation<void, number>({
    mutationKey: queryKeys.workouts.equipment(),
    mutationFn: (id) => deleteEquipment(id),
  })
}
