import { computed, type MaybeRefOrGetter, type Ref, toValue, watch } from 'vue'

/**
 * Numbered-pagination helper for a server-paginated list. Augments a caller-
 * owned `page` ref with the derived total page count and the clamp behaviour
 * every paginated list needs: when the total shrinks beneath the current page
 * (e.g. after deleting the last row on the final page), the page snaps back
 * into range. Shared so the paging maths and the clamp watcher live in one
 * tested place instead of being re-derived per view.
 *
 * The `page` is passed in (rather than created here) so it can drive the list
 * query while that query's total drives the page count, without a declaration
 * cycle. The page size is expected to come from the server-enforced
 * `num_records_per_page` setting (see `useRecordsPerPage`).
 *
 * @param page - The caller-owned 1-based current page ref.
 * @param total - Reactive total record count across all pages.
 * @param pageSize - Reactive records-per-page.
 * @returns The derived `totalPages` and a `reset` helper that returns to the
 *   first page (call when a filter changes the result set).
 */
export function useListPagination(
  page: Ref<number>,
  total: MaybeRefOrGetter<number>,
  pageSize: MaybeRefOrGetter<number>,
) {
  const totalPages = computed(() => {
    const size = Math.max(1, toValue(pageSize))
    return Math.max(1, Math.ceil(toValue(total) / size))
  })

  // Keep the page in range when the total shrinks beneath the current page.
  watch(totalPages, (pages) => {
    if (page.value > pages) {
      page.value = pages
    }
  })

  /** Returns to the first page; call when a filter changes the result set. */
  function reset(): void {
    page.value = 1
  }

  return { totalPages, reset }
}
