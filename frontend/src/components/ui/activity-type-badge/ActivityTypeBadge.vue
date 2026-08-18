<script setup lang="ts">
import { computed } from 'vue'
import type { HTMLAttributes } from 'vue'
import type { LucideIcon } from '@lucide/vue'

import { cn } from '@/lib/utils'

import type { ActivityBadgeType } from '.'
import { activityBadgeClasses } from '.'

interface Props {
  /** Activity category that determines the badge colour. */
  type: ActivityBadgeType
  /** Optional leading icon, e.g. from `activityTypeIcon`. */
  icon?: LucideIcon
  class?: HTMLAttributes['class']
}

const props = defineProps<Props>()

const colorClass = computed(() => activityBadgeClasses[props.type] ?? activityBadgeClasses.other)
</script>

<template>
  <span
    data-slot="activity-type-badge"
    :class="
      cn(
        'inline-flex items-center gap-1 rounded border border-transparent px-2 text-xs font-medium',
        colorClass,
        props.class,
      )
    "
  >
    <component :is="props.icon" v-if="props.icon" class="size-3.5 shrink-0" aria-hidden="true" />
    <slot />
  </span>
</template>
