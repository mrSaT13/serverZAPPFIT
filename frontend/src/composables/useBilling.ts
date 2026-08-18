import { readonly, ref, type DeepReadonly, type Ref } from 'vue'

import { createProviderSeam } from '@/composables/createProviderSeam'

/** Lifecycle state of a subscription. */
export type BillingStatus = 'active' | 'trialing' | 'past_due' | 'canceled'

/**
 * Current subscription summary for the signed-in account.
 *
 * @property plan - Plan identifier (e.g. `'free'`, `'pro'`).
 * @property status - Subscription lifecycle state.
 * @property renewsAt - ISO-8601 next renewal timestamp, or `null` if not set.
 */
export interface BillingState {
  plan: string
  status: BillingStatus
  renewsAt: string | null
}

/**
 * Pluggable billing source. Self-hosted instances have no billing and use the
 * default (always `null`); hosted/SaaS deployments register an adapter backed
 * by the subscription service so plan/status can drive UI (plan badges, upgrade
 * and past-due banners, gating of paid features).
 *
 * @property billing - Reactive subscription state, or `null` when not billed.
 */
export interface BillingAdapter {
  readonly billing: DeepReadonly<Ref<BillingState | null>>
}

/** Default adapter for non-billed (self-hosted) deployments: always `null`. */
const nullBillingAdapter: BillingAdapter = {
  billing: readonly(ref<BillingState | null>(null)),
}

const seam = createProviderSeam<BillingAdapter>(nullBillingAdapter)

/**
 * Registers the active billing adapter. Call once during bootstrap on billed
 * deployments.
 *
 * @param next - The adapter to install.
 */
export function setBillingAdapter(next: BillingAdapter): void {
  seam.set(next)
}

/** Result of {@link useBilling}. */
export interface UseBilling {
  /** Reactive subscription state, or `null` when not billed. */
  billing: DeepReadonly<Ref<BillingState | null>>
}

/**
 * Billing hook exposing reactive subscription state for billed deployments.
 *
 * @returns The active adapter's reactive `billing` (always `null` self-hosted).
 */
export function useBilling(): UseBilling {
  return { billing: seam.get().billing }
}
