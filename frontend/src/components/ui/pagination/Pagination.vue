<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronLeft, ChevronRight } from '@lucide/vue'

import { Button } from '@/components/ui/button'
import { PAGINATION_ELLIPSIS, paginationItems } from './pages'

const props = defineProps<{
  /** The current 1-based page. */
  page: number
  /** Total number of pages (at least 1). */
  totalPages: number
}>()

const emit = defineEmits<{ 'update:page': [page: number] }>()

const { t } = useI18n()

/**
 * The page items to render: page numbers interleaved with ellipsis markers
 * (see {@link paginationItems}).
 */
const items = computed(() => paginationItems(props.page, props.totalPages))

/**
 * Emits a page change, clamped to the valid range and ignoring no-ops.
 *
 * @param page - The requested 1-based page.
 */
function go(page: number): void {
  if (page < 1 || page > props.totalPages || page === props.page) {
    return
  }
  emit('update:page', page)
}
</script>

<template>
  <nav class="flex items-center justify-center gap-1" :aria-label="t('app.pagination.label')">
    <Button
      variant="outline"
      size="icon-sm"
      :disabled="page <= 1"
      :aria-label="t('app.pagination.previous')"
      @click="go(page - 1)"
    >
      <ChevronLeft class="size-4" aria-hidden="true" />
    </Button>

    <template
      v-for="(item, index) in items"
      :key="typeof item === 'number' ? item : `gap-${index}`"
    >
      <span v-if="item === PAGINATION_ELLIPSIS" class="px-2 text-hint" aria-hidden="true">{{
        item
      }}</span>
      <Button
        v-else
        :variant="item === page ? 'default' : 'outline'"
        size="icon-sm"
        :aria-current="item === page ? 'page' : undefined"
        :aria-label="t('app.pagination.goToPage', { page: item })"
        @click="go(item)"
      >
        {{ item }}
      </Button>
    </template>

    <Button
      variant="outline"
      size="icon-sm"
      :disabled="page >= totalPages"
      :aria-label="t('app.pagination.next')"
      @click="go(page + 1)"
    >
      <ChevronRight class="size-4" aria-hidden="true" />
    </Button>
  </nav>
</template>
