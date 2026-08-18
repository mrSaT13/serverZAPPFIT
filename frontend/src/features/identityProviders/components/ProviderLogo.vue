<script setup lang="ts">
import { computed, ref } from 'vue'
import { KeyRound } from '@lucide/vue'

import { resolveProviderLogo } from '@/features/identityProviders/utils/providerIcon'

const props = defineProps<{
  /** Builtin icon key or a custom icon URL, or `null`. */
  icon: string | null
  /** Provider name, used as the image alt text. */
  name: string
}>()

// A custom icon URL can 404; fall back to a generic key icon when it fails.
const failed = ref(false)
const src = computed(() => resolveProviderLogo(props.icon))
</script>

<template>
  <div
    class="flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-input bg-muted-foreground/15"
  >
    <img
      v-if="src && !failed"
      :src="src"
      :alt="name"
      class="size-full object-contain p-1"
      @error="failed = true"
    />
    <KeyRound v-else class="size-5 text-muted-foreground" aria-hidden="true" />
  </div>
</template>
