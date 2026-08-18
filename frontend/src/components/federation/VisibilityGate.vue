<script setup lang="ts">
import { computed } from 'vue'

import type { VisibilityLevel } from '@/types'

import { useAuthStore } from '@/features/auth/stores/auth'

/**
 * Gates its default slot behind a content visibility level. This is the single
 * source of truth for private/followers/unlisted/public/federated rendering,
 * so views never hand-roll `v-if` visibility checks.
 *
 * The follower/ownership policy is a placeholder until viewer-relationship data
 * is available; the real checks plug in here without touching call sites.
 */
const props = defineProps<{ level: VisibilityLevel }>()

const auth = useAuthStore()

const canView = computed(() => {
  switch (props.level) {
    case 'public':
    case 'unlisted':
    case 'federated':
      return true
    case 'followers':
    case 'private':
      return auth.isAuthenticated
    default:
      return false
  }
})
</script>

<template>
  <slot v-if="canView" />
  <slot v-else name="fallback" />
</template>
