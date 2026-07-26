<script setup lang="ts">
import type { FortuneChart } from '@/types'
defineProps<{ chart: FortuneChart }>()
const labels = { year: '年柱', month: '月柱', day: '日柱', hour: '时柱' }
const elementNames: Record<string, string> = { wood: '木', fire: '火', earth: '土', metal: '金', water: '水' }
</script>
<template>
  <section class="chart-section">
    <div class="section-heading"><span class="section-number">02</span><div><h2>四柱命盘</h2><p>公历 · 北京时间{{ chart.solar_time ? ` · 真太阳时 ${chart.solar_time.trueSolarTime}` : '' }}</p></div></div>
    <div class="pillars">
      <article v-for="(pillar, key) in chart.pillars" :key="key" :class="{ muted: !pillar }">
        <span>{{ labels[key as keyof typeof labels] }}</span><template v-if="pillar"><b>{{ pillar.stem }}</b><b>{{ pillar.branch }}</b><small>{{ pillar.stemTenGod }}</small></template><template v-else><b>—</b><b>—</b><small>时辰不详</small></template>
      </article>
    </div>
    <div class="chart-facts">
      <div><label>日主</label><strong>{{ chart.day_master.char }} · {{ elementNames[chart.day_master.element] }}{{ chart.day_master.polarity === 'yang' ? '阳' : '阴' }}</strong></div>
      <div><label>五行分布</label><span v-for="(count, key) in chart.five_elements" :key="key" class="element-chip">{{ elementNames[key] }} {{ count }}</span></div>
      <div><label>大运</label><strong>{{ chart.da_yun.isForward ? '顺排' : '逆排' }} · {{ chart.da_yun.startAge }} 岁起运</strong></div>
    </div>
    <div class="cycles"><span v-for="cycle in chart.da_yun.cycles.slice(0, 6)" :key="cycle.ganZhi"><b>{{ cycle.ganZhi }}</b><small>{{ cycle.startAge }}–{{ cycle.endAge }} 岁</small></span></div>
  </section>
</template>
