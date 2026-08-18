<script setup lang="ts">
import type { PrimitiveProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { Primitive } from 'reka-ui'

import { cn } from '@/lib/utils'

import type { CardVariants } from '.'
import { cardVariants } from '.'

interface Props extends PrimitiveProps {
  padding?: CardVariants['padding']
  class?: HTMLAttributes['class']
}

const props = withDefaults(defineProps<Props>(), {
  as: 'div',
})
</script>

<template>
  <Primitive
    data-slot="card"
    :as="as"
    :as-child="asChild"
    :class="cn(cardVariants({ padding }), props.class)"
  >
    <slot />
  </Primitive>
</template>
