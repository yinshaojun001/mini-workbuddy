<script setup lang="ts">
import ReadingReport from '@/components/ReadingReport.vue'

defineProps<{ content: string; streaming: boolean }>()
</script>

<template>
  <ReadingReport :content="content" :streaming="streaming" title="知梦解读" subtitle="传统参照与现实映照" section-number="03" />
</template>
