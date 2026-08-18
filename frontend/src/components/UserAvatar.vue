<script setup lang="ts">
import { ref, watch } from 'vue'
import { User } from '@lucide/vue'

import { Image } from '@/components/ui/image'
import { cn } from '@/lib/utils'

/**
 * Renders a user's profile photo, falling back to a generic user icon when no
 * photo is configured or the image fails to load (e.g. a stale path).
 *
 * The photo is rendered through {@link Image} so avatar URLs flow through the
 * active image-source seam (e.g. a CDN rewriter) like every other image.
 */
const props = withDefaults(
  defineProps<{
    /** Absolute avatar URL, or `null`/`undefined` when unset. */
    src: string | null | undefined
    /** Accessible alt text for the photo. */
    alt?: string
    /** Tailwind size utility applied to the photo frame, e.g. `size-6`. */
    sizeClass?: string
    /** Tailwind size utility applied to the fallback icon. */
    iconClass?: string
  }>(),
  { alt: '', sizeClass: 'size-6', iconClass: 'size-4' },
)

// Reset the failure flag whenever the source changes so a freshly uploaded
// photo is retried instead of staying on the fallback icon.
const failed = ref(false)
watch(
  () => props.src,
  () => {
    failed.value = false
  },
)
</script>

<template>
  <Image
    v-if="src && !failed"
    :src="src"
    :alt="alt"
    :class="cn('rounded-full object-cover', sizeClass)"
    @error="failed = true"
  />
  <User v-else :class="iconClass" />
</template>
