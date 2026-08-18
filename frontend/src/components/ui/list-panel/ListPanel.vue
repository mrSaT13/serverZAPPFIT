<script setup lang="ts">
import { computed } from 'vue'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ErrorState } from '@/components/ui/error-state'
import { Pagination } from '@/components/ui/pagination'
import { Skeleton } from '@/components/ui/skeleton'

/**
 * Reusable list-panel scaffold: one bordered card that owns the
 * loading → error → empty → list state machine plus the optional pagination
 * footer, so every list view stops re-implementing the same `v-if` ladder,
 * error wiring, and paging maths. Content is slot-driven; pair it with
 * `useListPagination` for the page/total-pages state.
 *
 * Slots: `header` (count + filters), `loading` (custom skeleton; a generic one
 * is provided), `empty` (the empty/zero-results content), default (the list
 * itself, typically a `<ul>`), and `footer` (shown for non-paginated panels,
 * e.g. an "add" action).
 */
const page = defineModel<number>('page', { default: 1 })

const props = withDefaults(
  defineProps<{
    /** Whether the backing query is loading its first data. */
    isLoading?: boolean
    /** Whether the backing query failed. */
    isError?: boolean
    /** Whether the loaded result set is empty. */
    isEmpty?: boolean
    /** Error-state heading (shown when `isError`). */
    errorTitle: string
    /** Optional error-state supporting copy. */
    errorDescription?: string
    /** Label for the error-state retry button. */
    retryLabel: string
    /** Whether to render the `header` slot; lets callers hide chrome per state. */
    showHeader?: boolean
    /** Whether this panel is paginated (renders the pagination footer). */
    paginated?: boolean
    /** Total page count, from `useListPagination`. */
    totalPages?: number
    /** Row count for the built-in loading skeleton. */
    loadingRows?: number
  }>(),
  {
    isLoading: false,
    isError: false,
    isEmpty: false,
    showHeader: true,
    paginated: false,
    totalPages: 1,
    loadingRows: 5,
  },
)

const emit = defineEmits<{
  /** The error-state retry affordance was activated. */
  retry: []
}>()

const showPagination = computed(
  () => props.paginated && !props.isLoading && !props.isError && props.totalPages > 1,
)
</script>

<template>
  <Card padding="none" class="divide-y divide-border overflow-hidden">
    <slot v-if="showHeader && $slots.header" name="header" />

    <!-- Loading -->
    <template v-if="isLoading">
      <slot name="loading">
        <div class="divide-y divide-border" aria-busy="true">
          <div v-for="n in loadingRows" :key="n" class="space-y-2 px-4 py-3">
            <Skeleton class="h-4 w-1/3" />
            <Skeleton class="h-3 w-1/5" />
          </div>
        </div>
      </slot>
    </template>

    <!-- Error -->
    <ErrorState
      v-else-if="isError"
      :title="errorTitle"
      :description="errorDescription"
      @retry="emit('retry')"
    >
      <template #action="{ retry }">
        <Button variant="outline" @click="retry">{{ retryLabel }}</Button>
      </template>
    </ErrorState>

    <!-- Empty -->
    <slot v-else-if="isEmpty" name="empty" />

    <!-- Ready: the list -->
    <slot v-else />

    <!-- Footer: pagination for paginated panels, else a custom footer slot. -->
    <div v-if="showPagination" class="px-4 py-3">
      <Pagination v-model:page="page" :total-pages="totalPages" />
    </div>
    <slot v-else-if="$slots.footer && !isLoading && !isError" name="footer" />
  </Card>
</template>
