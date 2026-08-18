<script setup lang="ts">
import { computed } from 'vue'
import { ArrowDown, ArrowUp } from '@lucide/vue'

import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

/**
 * A single health dashboard metric card. Shows a title, the metric value (or a
 * "no data" label), and a footer with one of two shapes: a target comparison
 * (an up/down arrow plus the target value, or a "no target" hint) when
 * `noTargetLabel` is supplied, otherwise free-form `footerText`.
 */
interface Props {
  /** The metric label shown at the top of the card. */
  title: string
  /** The formatted metric value, or `null` when there is no data. */
  value: string | null
  /** Label shown in place of the value when it is `null`. */
  noDataLabel: string
  /** Whether the metric is still loading (shows a skeleton). */
  isLoading?: boolean
  /** Optional secondary line beneath the value. */
  subtitle?: string | null
  /** The formatted target value (target mode), or `null` when none is set. */
  targetDisplayValue?: string | null
  /** Hint shown when no target is set; its presence enables target mode. */
  noTargetLabel?: string | null
  /** Free-form footer text (text mode, when `noTargetLabel` is absent). */
  footerText?: string | null
  /** Arrow direction comparing the value against its target. */
  arrowDirection?: 'up' | 'down' | null
}

const props = withDefaults(defineProps<Props>(), {
  isLoading: false,
  subtitle: null,
  targetDisplayValue: null,
  noTargetLabel: null,
  footerText: null,
  arrowDirection: null,
})

/** Target mode is active when a "no target" label is provided. */
const isTargetMode = computed(() => props.noTargetLabel !== null && props.noTargetLabel !== '')
</script>

<template>
  <Card class="flex flex-col gap-2">
    <p class="text-caption">{{ title }}</p>

    <Skeleton v-if="isLoading" class="h-7 w-24" />
    <p v-else-if="value !== null" class="text-metric font-medium text-foreground">{{ value }}</p>
    <p v-else class="text-body">{{ noDataLabel }}</p>

    <p v-if="subtitle && !isLoading" class="text-hint">{{ subtitle }}</p>

    <!-- Footer: target comparison (arrow + target) or free text. -->
    <div v-if="!isLoading" class="mt-auto pt-1">
      <template v-if="isTargetMode">
        <span v-if="targetDisplayValue" class="flex items-center gap-1 text-hint">
          <component
            :is="arrowDirection === 'down' ? ArrowDown : ArrowUp"
            v-if="arrowDirection"
            class="size-3.5 shrink-0"
            :class="arrowDirection === 'up' ? 'text-goal' : 'text-muted-foreground'"
            aria-hidden="true"
          />
          {{ targetDisplayValue }}
        </span>
        <span v-else class="text-hint">{{ noTargetLabel }}</span>
      </template>
      <span v-else-if="footerText" class="text-hint">{{ footerText }}</span>
    </div>
  </Card>
</template>
