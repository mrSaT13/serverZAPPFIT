<script setup lang="ts">
import type { Severity } from '@/types'

import { severityClasses } from '@/lib/severity'

defineProps<{ kind: Severity }>()
</script>

<template>
  <div
    class="rounded-input border px-3 py-2 text-meta"
    :class="severityClasses[kind]"
    role="status"
    aria-live="polite"
  >
    <slot />
  </div>
</template>
