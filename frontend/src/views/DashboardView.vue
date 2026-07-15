<script setup lang="ts">
import { Activity, ArrowRight, Bot, Boxes, CircleAlert, Wrench } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import type { Agent, ModelConfig, RunSummary, Skill, Tool } from '@/types'

const models = ref<ModelConfig[]>([]), agents = ref<Agent[]>([]), skills = ref<Skill[]>([]), tools = ref<Tool[]>([]), runs = ref<RunSummary[]>([])
const error = ref('')
const activeTools = computed(() => tools.value.filter(item => item.enabled).length)
onMounted(async () => {
  try { [models.value, agents.value, skills.value, tools.value, runs.value] = await Promise.all([api<ModelConfig[]>('/api/models'), api<Agent[]>('/api/agents'), api<Skill[]>('/api/skills'), api<Tool[]>('/api/tools'), api<RunSummary[]>('/api/runs')]) }
  catch (e) { error.value = (e as Error).message }
})
</script>

<template>
  <div class="page-heading">
    <div><div class="eyebrow">LOCAL AGENT WORKSPACE</div><h1>工作台</h1><p class="subtitle">本地模型、技能与智能体的实时概览。</p></div>
    <div class="actions"><RouterLink class="button button--lime" to="/agents/new"><Bot :size="15" />新建智能体</RouterLink></div>
  </div>
  <div v-if="error" class="error">{{ error }}</div>
  <section class="stats">
    <div class="stat"><div class="stat-value">{{ agents.length.toString().padStart(2, '0') }}</div><div class="stat-label">智能体</div></div>
    <div class="stat"><div class="stat-value">{{ models.filter(m => m.enabled).length.toString().padStart(2, '0') }}</div><div class="stat-label">可用模型配置</div></div>
    <div class="stat"><div class="stat-value">{{ skills.filter(s => s.enabled).length.toString().padStart(2, '0') }}</div><div class="stat-label">启用技能</div></div>
    <div class="stat"><div class="stat-value">{{ activeTools }}/3</div><div class="stat-label">启用工具</div></div>
  </section>
  <div class="split-grid">
    <section class="panel">
      <div class="panel-header"><h2>智能体工作区</h2><RouterLink class="button button--secondary" to="/agents">查看全部<ArrowRight :size="14" /></RouterLink></div>
      <div class="panel-body dashboard-list">
        <RouterLink v-for="agent in agents.slice(0, 5)" :key="agent.id" :to="`/agents/${agent.id}/run`" class="dashboard-row">
          <span class="agent-glyph">{{ agent.name.slice(0, 1) }}</span><span><b>{{ agent.name }}</b><small>{{ agent.work_directory }}</small></span><span class="badge" :class="agent.enabled ? 'badge--ok' : ''">{{ agent.enabled ? '可运行' : '已停用' }}</span>
        </RouterLink>
        <div v-if="!agents.length" class="empty"><div><Bot /><h2>还没有智能体</h2><p>创建一个智能体开始工作。</p></div></div>
      </div>
    </section>
    <section class="panel">
      <div class="panel-header"><h2>最近运行</h2><Activity :size="16" /></div>
      <div class="panel-body">
        <div v-for="run in runs.slice(0, 6)" :key="run.id" class="compact-row"><span class="status-pip" :class="run.status" /><span><b>{{ run.status === 'completed' ? '运行完成' : run.status === 'failed' ? '运行失败' : '运行中' }}</b><small>{{ run.event_count }} 个事件</small></span></div>
        <div v-if="!runs.length" class="quiet-state"><CircleAlert :size="18" /><span>暂无运行记录</span></div>
      </div>
    </section>
  </div>
  <div class="quick-links">
    <RouterLink to="/skills"><Boxes :size="16" /><span><b>技能目录</b><small>管理 {{ skills.length }} 个本地技能</small></span></RouterLink>
    <RouterLink to="/tools"><Wrench :size="16" /><span><b>工具权限</b><small>写入和命令始终需要审批</small></span></RouterLink>
  </div>
</template>

<style scoped>
.dashboard-list{padding:0}.dashboard-row{min-height:63px;padding:10px 14px;display:grid;grid-template-columns:34px minmax(0,1fr) auto;align-items:center;gap:10px;border-bottom:1px solid var(--line);color:inherit;text-decoration:none}.dashboard-row>span:nth-child(2){min-width:0}.dashboard-row:hover{background:#f8faf7}.dashboard-row:last-child{border:0}.agent-glyph{width:32px;height:32px;display:grid;place-items:center;background:#e4f2cc;color:#395214;font-weight:800;font-size:12px}.dashboard-row b,.compact-row b{display:block;font-size:12px}.dashboard-row small,.compact-row small{display:block;color:var(--muted);font:9px/1.5 ui-monospace,monospace;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.compact-row{display:flex;align-items:center;gap:9px;padding:8px 0;border-bottom:1px solid #e8ebe8}.compact-row:last-child{border:0}.status-pip{width:7px;height:7px;border-radius:50%;background:var(--amber)}.status-pip.completed{background:var(--mint)}.status-pip.failed{background:var(--brick)}.quiet-state{min-height:120px;display:flex;align-items:center;justify-content:center;gap:8px;color:var(--muted);font-size:11px}.quick-links{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-top:16px}.quick-links a{display:flex;gap:11px;align-items:center;padding:15px 17px;border:1px solid var(--line);background:white;color:inherit;text-decoration:none;border-radius:var(--radius)}.quick-links a:hover{border-color:var(--line-dark);transform:translateY(-1px)}.quick-links b,.quick-links small{display:block}.quick-links b{font-size:12px}.quick-links small{color:var(--muted);font-size:10px;margin-top:3px}@media(max-width:600px){.quick-links{grid-template-columns:1fr}}
</style>
