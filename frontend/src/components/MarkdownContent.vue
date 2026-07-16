<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/markdown/renderMarkdown'

const props = defineProps<{ content: string }>()
const html = computed(() => renderMarkdown(props.content))
</script>

<template>
  <div class="message-content markdown-content" v-html="html" />
</template>

<style scoped>
.markdown-content {
  overflow-wrap: anywhere;
  white-space: normal;
}

.markdown-content :deep(> :first-child) { margin-top: 0; }
.markdown-content :deep(> :last-child) { margin-bottom: 0; }
.markdown-content :deep(p) { margin: 0 0 9px; }
.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  margin: 17px 0 8px;
  color: var(--ink);
  font-weight: 750;
  line-height: 1.35;
}
.markdown-content :deep(h1) { font-size: 17px; }
.markdown-content :deep(h2) { font-size: 15px; }
.markdown-content :deep(h3) { font-size: 13px; }
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) { font-size: 12px; }
.markdown-content :deep(ul),
.markdown-content :deep(ol) { margin: 8px 0; padding-left: 22px; }
.markdown-content :deep(li) { margin: 3px 0; }
.markdown-content :deep(li > p) { margin: 0; }
.markdown-content :deep(blockquote) {
  margin: 10px 0;
  padding: 7px 11px;
  border-left: 3px solid var(--mint);
  background: #f7faf7;
  color: #4d5b53;
}
.markdown-content :deep(code) {
  border: 1px solid #d4dad5;
  border-radius: 3px;
  background: #f5f7f4;
  padding: 1px 4px;
  color: #314039;
  font: 10px/1.55 ui-monospace, SFMono-Regular, Menlo, monospace;
}
.markdown-content :deep(pre) {
  max-width: 100%;
  margin: 10px 0;
  overflow-x: auto;
  border: 1px solid #313a34;
  border-radius: 4px;
  background: #202622;
  padding: 12px 13px;
  color: #e4ebe6;
  white-space: pre;
  line-height: 1.65;
}
.markdown-content :deep(pre code) {
  border: 0;
  background: transparent;
  padding: 0;
  color: inherit;
}
.markdown-content :deep(table) {
  display: block;
  width: max-content;
  max-width: 100%;
  margin: 10px 0;
  overflow-x: auto;
  border-collapse: collapse;
}
.markdown-content :deep(th),
.markdown-content :deep(td) {
  min-width: 90px;
  border: 1px solid #cfd5d0;
  padding: 6px 9px;
  text-align: left;
}
.markdown-content :deep(th) { background: #e8ece8; font-weight: 700; }
.markdown-content :deep(a) {
  color: #236f5d;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.markdown-content :deep(hr) { margin: 14px 0; border: 0; border-top: 1px solid var(--line); }
.markdown-content :deep(img) { max-width: 100%; height: auto; }
</style>

