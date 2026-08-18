import { createProviderSeam } from '@/composables/createProviderSeam'

type TelemetryData = Record<string, unknown>

/**
 * Pluggable telemetry sink. Self-hosted instances use the default no-op;
 * hosted/SaaS deployments register an adapter (web-vitals, error tracking).
 *
 * @property captureError - Reports a caught error with optional context.
 * @property trackEvent - Records a named product/usage event.
 */
export interface TelemetryAdapter {
  captureError(error: unknown, context?: TelemetryData): void
  trackEvent(name: string, data?: TelemetryData): void
}

const noopAdapter: TelemetryAdapter = {
  captureError(error, context) {
    console.error('[telemetry] error', error, context)
  },
  trackEvent(name, data) {
    if (import.meta.env.DEV) {
      console.debug('[telemetry] event', name, data)
    }
  },
}

const seam = createProviderSeam<TelemetryAdapter>(noopAdapter)

/**
 * Registers the active telemetry adapter. Call once during bootstrap on
 * deployments that ship real telemetry.
 *
 * @param next - The adapter to install.
 */
export function setTelemetryAdapter(next: TelemetryAdapter): void {
  seam.set(next)
}

/**
 * Telemetry hook exposing error capture and event tracking.
 *
 * @returns The active adapter's `captureError` and `trackEvent` functions.
 */
export function useTelemetry(): TelemetryAdapter {
  return {
    captureError: (error, context) => seam.get().captureError(error, context),
    trackEvent: (name, data) => seam.get().trackEvent(name, data),
  }
}
