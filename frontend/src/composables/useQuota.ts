import { readonly, ref, type DeepReadonly, type Ref } from 'vue'

import { createProviderSeam } from '@/composables/createProviderSeam'

/**
 * Usage/limit for a single metered resource (storage, activities, API calls…).
 *
 * @property used - Amount currently consumed, in `unit`.
 * @property limit - Allowance in `unit`, or `null` for unlimited.
 * @property unit - Unit the figures are expressed in (e.g. `'bytes'`, `'count'`).
 */
export interface QuotaResource {
  used: number
  limit: number | null
  unit: string
}

/** Current usage keyed by resource name (e.g. `'storage'`, `'activities'`). */
export type QuotaSnapshot = Record<string, QuotaResource>

/**
 * Pluggable quota source. Self-hosted instances are unmetered and use the
 * default (always `null`); hosted/SaaS deployments register an adapter backed
 * by the billing/usage service so plan limits can drive UI (progress bars,
 * upgrade prompts, upload gating).
 *
 * @property quota - Reactive current usage, or `null` when unmetered/unknown.
 */
export interface QuotaAdapter {
  readonly quota: DeepReadonly<Ref<QuotaSnapshot | null>>
}

/** Default adapter for unmetered (self-hosted) deployments: always `null`. */
const nullQuotaAdapter: QuotaAdapter = {
  quota: readonly(ref<QuotaSnapshot | null>(null)),
}

const seam = createProviderSeam<QuotaAdapter>(nullQuotaAdapter)

/**
 * Registers the active quota adapter. Call once during bootstrap on metered
 * deployments.
 *
 * @param next - The adapter to install.
 */
export function setQuotaAdapter(next: QuotaAdapter): void {
  seam.set(next)
}

/** Result of {@link useQuota}. */
export interface UseQuota {
  /** Reactive current usage, or `null` when unmetered/unknown. */
  quota: DeepReadonly<Ref<QuotaSnapshot | null>>
}

/**
 * Quota hook exposing reactive resource usage for metered deployments.
 *
 * @returns The active adapter's reactive `quota` (always `null` self-hosted).
 */
export function useQuota(): UseQuota {
  return { quota: seam.get().quota }
}
