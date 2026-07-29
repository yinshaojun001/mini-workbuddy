<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/markdown'
const props = withDefaults(defineProps<{ content: string; streaming: boolean; title?: string; subtitle?: string; sectionNumber?: string }>(), {
  title: '命理解读',
  subtitle: '传统解释与现实建议',
  sectionNumber: '03',
})
const html = computed(() => renderMarkdown(props.content))
</script>
<template><section class="reading"><div class="section-heading"><span class="section-number">{{ sectionNumber }}</span><div><h2>{{ title }}</h2><p>{{ subtitle }}</p></div><span v-if="streaming" class="stream-status"><i />生成中</span></div><div v-if="content" class="markdown" v-html="html" /><div v-else class="report-placeholder"><span /><span /><span /></div></section></template>
