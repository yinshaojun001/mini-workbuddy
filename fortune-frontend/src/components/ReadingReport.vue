<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/markdown'
const props = defineProps<{ content: string; streaming: boolean }>()
const html = computed(() => renderMarkdown(props.content))
</script>
<template><section class="reading"><div class="section-heading"><span class="section-number">03</span><div><h2>命理解读</h2><p>传统解释与现实建议</p></div><span v-if="streaming" class="stream-status"><i />生成中</span></div><div v-if="content" class="markdown" v-html="html" /><div v-else class="report-placeholder"><span /><span /><span /></div></section></template>
