import {
  MutationCache,
  QueryCache,
  QueryClient,
  VueQueryPlugin,
  type VueQueryPluginOptions,
} from '@tanstack/vue-query'

import { useTelemetry } from '@/composables/useTelemetry'

/**
 * Shared query client. Server state (caching, dedupe, background refetch,
 * invalidation) flows through TanStack Query; Pinia stays client-only.
 *
 * Cache-level `onError` handlers forward every failed query and mutation to the
 * telemetry adapter so observability is centralised rather than repeated in each
 * call site. Only the (token-free) query/mutation key is attached as context;
 * raw variables and responses are never forwarded.
 */
export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      useTelemetry().captureError(error, { scope: 'query', queryKey: query.queryKey })
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      useTelemetry().captureError(error, {
        scope: 'mutation',
        mutationKey: mutation.options.mutationKey,
      })
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

export const vueQueryOptions: VueQueryPluginOptions = { queryClient }

export { VueQueryPlugin }
