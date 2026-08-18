<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { DropdownMenuSeparator, type DropdownMenuSeparatorProps } from 'reka-ui'

import { cn } from '@/lib/utils'

const props = defineProps<DropdownMenuSeparatorProps & { class?: HTMLAttributes['class'] }>()
</script>

<template>
  <DropdownMenuSeparator
    data-slot="dropdown-menu-separator"
    :as="props.as"
    :as-child="props.asChild"
    :class="cn('-mx-1 my-1 h-px bg-border', props.class)"
  />
</template>
