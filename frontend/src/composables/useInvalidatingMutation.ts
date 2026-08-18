import { useMutation, useQueryClient } from '@tanstack/vue-query'

/** Options for {@link useInvalidatingMutation}. */
export interface InvalidatingMutationOptions<TData, TVariables> {
  /** Mutation identity key (used for dedupe/observability). */
  mutationKey: readonly unknown[]
  /** The async write to perform. */
  mutationFn: (variables: TVariables) => Promise<TData>
  /**
   * Query key to invalidate once the mutation settles. Defaults to
   * `mutationKey`. Pass a broader domain prefix (e.g. `queryKeys.gears.all()`)
   * when a write should cascade to lists, detail, and derived totals.
   */
  invalidateKey?: readonly unknown[]
}

/**
 * Standard "write then invalidate" mutation — the reference pattern for
 * server-computed resources where an optimistic update would be guesswork
 * (the create/update/delete operations behind every CRUD domain). On settle it
 * invalidates the chosen domain key so every affected list, search, and detail
 * query refetches the server-authoritative state.
 *
 * Use the optimistic reference in `@/features/notifications/composables`
 * instead when the result is knowable client-side and instant feedback matters.
 *
 * @typeParam TData - The mutation's resolved value.
 * @typeParam TVariables - The mutation's input variables.
 * @param options - Mutation key, the write function, and the invalidation key.
 * @returns The TanStack Query mutation.
 */
export function useInvalidatingMutation<TData, TVariables>(
  options: InvalidatingMutationOptions<TData, TVariables>,
) {
  const client = useQueryClient()
  const invalidateKey = options.invalidateKey ?? options.mutationKey

  return useMutation<TData, Error, TVariables>({
    mutationKey: options.mutationKey,
    mutationFn: options.mutationFn,
    onSettled: () => {
      void client.invalidateQueries({ queryKey: invalidateKey })
    },
  })
}
