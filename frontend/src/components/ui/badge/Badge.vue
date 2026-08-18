<script setup lang="ts">
import type { PrimitiveProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'

import { Primitive } from 'reka-ui'

import { cn } from '@/lib/utils'

import type { BadgeVariants } from '.'
import { badgeVariants } from '.'

interface Props extends PrimitiveProps {
  /** The visual style of the badge. */
  variant?: BadgeVariants['variant']
  class?: HTMLAttributes['class']
}

const props = withDefaults(defineProps<Props>(), {
  as: 'span',
})
</script>

<template>
  <Primitive
    data-slot="badge"
    :data-variant="variant"
    :as="as"
    :as-child="asChild"
    :class="cn(badgeVariants({ variant }), props.class)"
  >
    <slot />
  </Primitive>
</template>
