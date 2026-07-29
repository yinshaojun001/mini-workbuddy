<script setup lang="ts">
import type { DreamPublicContext } from '@/types'

defineProps<{ context: DreamPublicContext; dreamText?: string }>()

function excerpt(value: string) {
  return value.length > 120 ? `${value.slice(0, 120)}...` : value
}
</script>

<template>
  <section class="dream-context">
    <div class="section-heading"><span class="section-number">02</span><div><h2>梦境速写</h2><p>情绪与传统意象标签</p></div></div>
    <div class="dream-context-grid">
      <article>
        <label>梦境</label>
        <p>{{ dreamText ? excerpt(dreamText) : '已记录本次梦境正文' }}</p>
      </article>
      <article>
        <label>情绪</label>
        <div class="dream-tags"><span v-for="emotion in context.summary.emotions" :key="emotion">{{ emotion }}</span><span v-if="!context.summary.emotions.length">未选择</span></div>
      </article>
      <article>
        <label>重复梦</label>
        <p>{{ context.summary.recurring ? '是' : '否' }}</p>
      </article>
    </div>
    <div class="dream-symbols">
      <label>传统意象</label>
      <div class="dream-tags"><span v-for="symbol in context.symbols" :key="symbol.id">{{ symbol.label }}</span><span v-if="!context.symbols.length">未命中</span></div>
      <small>索引版本 {{ context.reference_index_version }}</small>
    </div>
  </section>
</template>
