import { onScopeDispose, watch, type Ref } from 'vue'

/** Tuning options for {@link useInfiniteScroll}. */
export interface UseInfiniteScrollOptions {
  /**
   * Distance from the viewport at which the sentinel is considered "visible",
   * so the next page is fetched before the user reaches the very bottom.
   */
  rootMargin?: string
  /**
   * Gate evaluated on each intersection; when it returns `false` the callback
   * is skipped. Use it to stop loading once there is no next page or a fetch is
   * already in flight.
   */
  enabled?: () => boolean
}

/**
 * Reusable infinite-scroll primitive: observes a sentinel element and invokes
 * `onIntersect` whenever it scrolls into view. Built on `IntersectionObserver`
 * so it costs nothing while the sentinel is off-screen, and re-binds whenever
 * the target ref changes (e.g. when the list switches between empty and loaded
 * states). The observer is torn down automatically when the owning scope is
 * disposed, so callers never leak listeners.
 *
 * Designed to be the shared list-loading seam every paginated view copies, so
 * pagination behaves identically across notifications, activities, gear, etc.
 *
 * @param target - Ref to the sentinel element placed at the end of the list.
 * @param onIntersect - Called when the sentinel becomes visible and `enabled`
 *   (if provided) returns `true`.
 * @param options - Optional root margin and an `enabled` gate.
 */
export function useInfiniteScroll(
  target: Ref<HTMLElement | null>,
  onIntersect: () => void,
  options: UseInfiniteScrollOptions = {},
): void {
  const { rootMargin = '200px', enabled } = options
  let observer: IntersectionObserver | null = null

  function disconnect(): void {
    observer?.disconnect()
    observer = null
  }

  watch(
    target,
    (element) => {
      disconnect()
      // SSR/test environments without IntersectionObserver simply no-op; the
      // view's manual "load more" button remains the accessible fallback.
      if (!element || typeof IntersectionObserver === 'undefined') {
        return
      }
      observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting && (enabled?.() ?? true)) {
              onIntersect()
            }
          }
        },
        { rootMargin },
      )
      observer.observe(element)
    },
    // `flush: 'post'` so the DOM node exists before we observe it.
    { immediate: true, flush: 'post' },
  )

  onScopeDispose(disconnect)
}
