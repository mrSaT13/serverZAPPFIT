<script setup lang="ts">
/**
 * Single chokepoint for rendering text that may originate from a remote
 * instance (activity descriptions, comments, profile bios).
 *
 * By default it renders as plain text, which is XSS-safe. When `markdown` is
 * set, the source is parsed and sanitized (DOMPurify, strict allow-list) by
 * {@link renderMarkdown} and injected via `v-html` — the ONLY place `v-html` is
 * permitted in the app. Centralising it here keeps the federated-content attack
 * surface to one reviewable file.
 */
import { computed } from 'vue'

import { renderMarkdown } from '@/utils/markdown'

const props = withDefaults(
  defineProps<{ source?: string | null; as?: string; markdown?: boolean }>(),
  {
    as: 'p',
    source: '',
    markdown: false,
  },
)

const html = computed(() => (props.markdown ? renderMarkdown(props.source) : ''))
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html -- Sanitized by DOMPurify in renderMarkdown; this is the audited single v-html chokepoint. -->
  <div v-if="markdown" class="markdown-content" v-html="html" />
  <component :is="as" v-else>{{ source ?? '' }}</component>
</template>

<style scoped>
.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  margin-top: 0.5em;
  margin-bottom: 0.25em;
  font-weight: 500;
}

.markdown-content :deep(h1) {
  font-size: 1.25em;
}

.markdown-content :deep(h2) {
  font-size: 1.15em;
}

.markdown-content :deep(h3) {
  font-size: 1.05em;
}

.markdown-content :deep(p) {
  margin-bottom: 0.5em;
}

.markdown-content :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  padding-left: 1.5em;
  margin-bottom: 0.5em;
}

.markdown-content :deep(ul) {
  list-style: disc;
}

.markdown-content :deep(ol) {
  list-style: decimal;
}

.markdown-content :deep(li) {
  margin-bottom: 0.125em;
}

.markdown-content :deep(a) {
  color: var(--color-brand);
  text-decoration: underline;
}

.markdown-content :deep(blockquote) {
  border-left: 3px solid var(--color-border);
  padding-left: 1em;
  margin-left: 0;
  color: var(--color-muted-foreground);
}

.markdown-content :deep(code) {
  background-color: var(--color-muted);
  padding: 0.125em 0.25em;
  border-radius: 0.25em;
  font-size: 0.875em;
}

.markdown-content :deep(pre) {
  background-color: var(--color-muted);
  padding: 0.75em;
  border-radius: 0.375em;
  overflow-x: auto;
  margin-bottom: 0.5em;
}

.markdown-content :deep(pre code) {
  background-color: transparent;
  padding: 0;
}

.markdown-content :deep(table) {
  width: 100%;
  margin-bottom: 0.5em;
  border-collapse: collapse;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 1px solid var(--color-border);
  padding: 0.375em 0.75em;
}

.markdown-content :deep(hr) {
  margin: 0.75em 0;
  border: 0;
  border-top: 1px solid var(--color-border);
}
</style>
