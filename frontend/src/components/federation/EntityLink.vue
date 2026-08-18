<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

/**
 * Resolves an entity reference to a navigation target. Local references (a
 * router path beginning with `/`) become router links; federated URNs
 * (`actor@instance/entity-id`) render as inert references until federated
 * routing exists. Keeping resolution here means call sites never branch on
 * local-vs-remote themselves.
 */
const props = defineProps<{ urn: string }>()

const isLocal = computed(() => props.urn.startsWith('/') && !props.urn.includes('@'))
</script>

<template>
  <RouterLink v-if="isLocal" :to="urn">
    <slot />
  </RouterLink>
  <span v-else class="cursor-not-allowed opacity-70" :title="urn">
    <slot />
  </span>
</template>
