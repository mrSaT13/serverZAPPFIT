import { readonly, ref } from 'vue'

import type { Severity } from '@/types'

/** A transient toast notification. */
export interface Toast {
  id: number
  kind: Severity
  message: string
}

const DEFAULT_DURATION_MS = 5000

const toasts = ref<Toast[]>([])
let nextId = 0

/**
 * App-wide toast notifications. Module-level state means any layer (services,
 * stores, composables, the global error handler) can surface user feedback
 * without prop drilling, while a single {@link Toast} list renders in one host.
 *
 * @returns The reactive toast list plus dispatch and dismiss helpers.
 */
export function useToasts() {
  /**
   * Removes a toast by id.
   *
   * @param id - The toast id to dismiss.
   */
  function dismiss(id: number): void {
    toasts.value = toasts.value.filter((toast) => toast.id !== id)
  }

  /**
   * Queues a toast, auto-dismissing it after `duration` unless `duration` is 0.
   *
   * @param kind - Severity of the toast.
   * @param message - User-facing message.
   * @param duration - Auto-dismiss delay in ms; `0` keeps it until dismissed.
   * @returns The new toast id.
   */
  function notify(kind: Severity, message: string, duration = DEFAULT_DURATION_MS): number {
    nextId += 1
    const id = nextId
    toasts.value = [...toasts.value, { id, kind, message }]
    if (duration > 0) {
      window.setTimeout(() => dismiss(id), duration)
    }
    return id
  }

  return {
    toasts: readonly(toasts),
    notify,
    dismiss,
    /** Shows a success toast. */
    success: (message: string, duration?: number) => notify('success', message, duration),
    /** Shows an error toast. */
    error: (message: string, duration?: number) => notify('error', message, duration),
    /** Shows an info toast. */
    info: (message: string, duration?: number) => notify('info', message, duration),
    /** Shows a warning toast. */
    warning: (message: string, duration?: number) => notify('warning', message, duration),
  }
}
