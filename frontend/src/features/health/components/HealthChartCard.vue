<script setup lang="ts">
import { Card } from '@/components/ui/card'

defineProps<{
  /** Heading shown beside the accent dot. */
  title: string
  /** Accent-dot colour (a resolved theme hex). */
  accentColor: string
}>()
</script>

<template>
  <Card class="flex min-w-0 flex-col gap-3">
    <div class="flex items-center gap-2">
      <span
        class="size-2.5 rounded-full"
        :style="{ backgroundColor: accentColor }"
        aria-hidden="true"
      />
      <h3 class="text-card-heading">{{ title }}</h3>
    </div>
    <!-- The metric's canvas container is provided by the parent chart. -->
    <slot />
  </Card>
</template>
