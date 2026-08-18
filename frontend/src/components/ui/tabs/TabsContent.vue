<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { computed } from 'vue'
import { TabsContent, type TabsContentProps, useForwardProps } from 'reka-ui'

import { cn } from '@/lib/utils'

const props = defineProps<TabsContentProps & { class?: HTMLAttributes['class'] }>()

const delegatedProps = computed(() => {
  const { class: _class, ...delegated } = props
  return delegated
})

const forwarded = useForwardProps(delegatedProps)
</script>

<template>
  <TabsContent
    data-slot="tabs-content"
    v-bind="forwarded"
    :class="cn('mt-4 outline-none', props.class)"
  >
    <slot />
  </TabsContent>
</template>
