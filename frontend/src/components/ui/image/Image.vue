<script setup lang="ts">
import { computed, type HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'
import { resolveImageSource, resolveImageSrcset } from './imageSource'

const props = withDefaults(
  defineProps<{
    /** Image URL; rewritten through the active image source resolver. */
    src: string
    /** Required alternative text for accessibility (use `''` for decorative). */
    alt: string
    /** Optional responsive candidates; each URL is resolved through the seam. */
    srcset?: string
    /** Optional `sizes` hint paired with `srcset`. */
    sizes?: string
    /** Intrinsic width, in pixels, to reserve layout space and avoid shift. */
    width?: number | string
    /** Intrinsic height, in pixels, to reserve layout space and avoid shift. */
    height?: number | string
    /** Native loading strategy. Defaults to lazy. */
    loading?: 'lazy' | 'eager'
    /** Native decoding hint. Defaults to async. */
    decoding?: 'async' | 'sync' | 'auto'
    /** Extra classes merged onto the `<img>`. */
    class?: HTMLAttributes['class']
  }>(),
  {
    srcset: undefined,
    sizes: undefined,
    width: undefined,
    height: undefined,
    loading: 'lazy',
    decoding: 'async',
    class: undefined,
  },
)

const resolvedSrc = computed(() => resolveImageSource(props.src))
const resolvedSrcset = computed(() => (props.srcset ? resolveImageSrcset(props.srcset) : undefined))
</script>

<template>
  <img
    data-slot="image"
    :src="resolvedSrc"
    :srcset="resolvedSrcset"
    :sizes="sizes"
    :alt="alt"
    :width="width"
    :height="height"
    :loading="loading"
    :decoding="decoding"
    :class="cn(props.class)"
  />
</template>
