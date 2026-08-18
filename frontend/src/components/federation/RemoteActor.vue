<script setup lang="ts">
import { computed } from 'vue'

/**
 * Renders any actor (`name` or fediverse-style `name@instance`) with correct
 * provenance: local actors show just their name, remote actors carry an
 * instance badge. Centralising this keeps local-vs-remote presentation
 * consistent everywhere an actor is shown.
 */
const props = defineProps<{ handle: string }>()

const parsed = computed(() => {
  const trimmed = props.handle.replace(/^@/, '')
  const separatorIndex = trimmed.lastIndexOf('@')
  if (separatorIndex <= 0) {
    return { name: trimmed, instance: null as string | null }
  }
  return {
    name: trimmed.slice(0, separatorIndex),
    instance: trimmed.slice(separatorIndex + 1) || null,
  }
})
</script>

<template>
  <span class="inline-flex items-center gap-1">
    <span>{{ parsed.name }}</span>
    <span
      v-if="parsed.instance"
      class="rounded-badge bg-muted px-1.5 py-0.5 text-micro text-muted-foreground"
      :title="parsed.instance"
    >
      {{ parsed.instance }}
    </span>
  </span>
</template>
