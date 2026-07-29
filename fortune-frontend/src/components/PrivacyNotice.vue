<script setup lang="ts">
import type { PublicAppSlug } from '@/types'

withDefaults(defineProps<{ kind?: PublicAppSlug }>(), { kind: 'fortune' })
</script>

<template>
  <section class="notice-band">
    <b>说明</b>
    <template v-if="kind === 'fortune'">
      <p>命理解读属于传统文化娱乐内容，不构成医疗、法律、投资或人生决策建议。涉及健康、安全和财务风险时，请咨询具备资质的专业人士。</p>
      <p>出生资料和对话只用于本次匿名会话，公开会话 24 小时后自动清除，也可以主动删除。</p>
      <p>排盘计算由 <a href="https://openfate.ai" target="_blank" rel="noopener noreferrer">OpenFate.ai</a> 确定性引擎提供；城市经度数据来自 GeoNames，采用 CC BY 4.0。</p>
    </template>
    <template v-else>
      <p>梦境解读属于传统文化参照与自我反思内容，不构成医疗、心理诊断、法律、投资或人生决策建议。涉及健康、安全和财务风险时，请咨询具备资质的专业人士。</p>
      <p>梦境正文、近期背景和对话用于生成本次解读，公开会话 24 小时后自动清除，也可以主动删除。</p>
      <p>传统梦象参考整理自公版《周公解梦》，只作文化参照；心理与现实映照不是诊断或预言。</p>
    </template>
  </section>
</template>
