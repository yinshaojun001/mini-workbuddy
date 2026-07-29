<script setup lang="ts">
import { AppWindow, Copy, ExternalLink, Pencil, Plus, Trash2, X } from 'lucide-vue-next'
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '@/api/client'
import type { Agent, PublishedApp, RuntimeAdapter } from '@/types'

const items = ref<PublishedApp[]>([])
const agents = ref<Agent[]>([])
const error = ref('')
const message = ref('')
const loading = ref(false)
const showForm = ref(false)
const editing = ref<PublishedApp | null>(null)
const form = reactive({ name: '', slug: '', agent_id: '', runtime_adapter: 'fortune' as RuntimeAdapter, enabled: true, daily_limit: 3, ttl_hours: 24, max_questions: 20 })

const enabledAgents = computed(() => agents.value.filter((item) => item.enabled))
const healthText = {
  ready: '可发布',
  disabled: '已停用',
  agent_unavailable: 'Agent 不可用',
  model_unavailable: '模型未就绪',
  adapter_unavailable: '运行适配器不可用',
  reference_unavailable: '梦象资料不可用',
}
const adapterText:Record<RuntimeAdapter,string>={fortune:'八字排盘',dream:'梦境解读'}
const builtinAdapterLocked=computed(()=>editing.value?.id==='fortune'||editing.value?.id==='dream')

async function load() {
  error.value = ''
  try {
    const [appItems, agentItems] = await Promise.all([
      api<PublishedApp[]>('/api/apps'),
      api<Agent[]>('/api/agents'),
    ])
    items.value = appItems
    agents.value = agentItems
  } catch (reason) {
    error.value = (reason as Error).message
  }
}

function agentName(id: string) {
  return agents.value.find((item) => item.id === id)?.name || 'Agent 不存在'
}

function open(item?: PublishedApp) {
  editing.value = item || null
  Object.assign(form, item ? {
    name: item.name,
    slug: item.slug,
    agent_id: item.agent_id,
    runtime_adapter: item.runtime_adapter,
    enabled: item.enabled,
    daily_limit: item.daily_limit,
    ttl_hours: item.ttl_hours,
    max_questions: item.max_questions,
  } : {
    name: '',
    slug: '',
    agent_id: enabledAgents.value[0]?.id || '',
    runtime_adapter: 'fortune',
    enabled: true,
    daily_limit: 3,
    ttl_hours: 24,
    max_questions: 20,
  })
  showForm.value = true
}

async function save() {
  loading.value = true
  error.value = ''
  try {
    const path = editing.value ? `/api/apps/${editing.value.id}` : '/api/apps'
    await api(path, { method: editing.value ? 'PUT' : 'POST', body: JSON.stringify(form) })
    showForm.value = false
    message.value = '发布应用已保存'
    await load()
  } catch (reason) {
    error.value = (reason as Error).message
  } finally {
    loading.value = false
  }
}

async function remove(item: PublishedApp) {
  if (!confirm(`确定删除“${item.name}”吗？Agent 和管理数据不会被删除。`)) return
  try {
    await api(`/api/apps/${item.id}`, { method: 'DELETE' })
    message.value = '发布应用已删除'
    await load()
  } catch (reason) {
    error.value = (reason as Error).message
  }
}

async function copyUrl(item: PublishedApp) {
  try {
    await navigator.clipboard.writeText(item.public_url)
    message.value = '公开地址已复制'
  } catch {
    error.value = '无法复制地址，请手动复制'
  }
}

onMounted(load)
</script>

<template>
  <div class="page-heading">
    <div>
      <div class="eyebrow">PUBLISHED APPS</div>
      <h1>发布应用</h1>
      <p class="subtitle">将固定 Agent 发布为隔离的公开体验。</p>
    </div>
    <button class="button button--lime" @click="open()"><Plus :size="15" />新建应用</button>
  </div>

  <div v-if="message" class="notice">{{ message }}</div>
  <div v-if="error" class="error">{{ error }}</div>

  <div v-if="items.length" class="table-wrap">
    <table class="data-table app-table">
      <thead><tr><th>应用</th><th>运行类型</th><th>绑定 Agent</th><th>访问策略</th><th>状态</th><th>公开地址</th><th></th></tr></thead>
      <tbody>
        <tr v-for="item in items" :key="item.id">
          <td><div class="primary-cell">{{ item.name }}</div><div class="cell-sub">/{{ item.slug }}</div></td>
          <td>{{adapterText[item.runtime_adapter]}}</td>
          <td>{{ agentName(item.agent_id) }}</td>
          <td><div>{{ item.daily_limit }} 次/日 · {{ item.max_questions }} 次追问</div><div class="cell-sub">保存 {{ item.ttl_hours }} 小时</div></td>
          <td><span class="badge" :class="item.health === 'ready' ? 'badge--ok' : item.health === 'disabled' ? '' : 'badge--warn'">{{ healthText[item.health] }}</span></td>
          <td><a class="public-link" :href="item.public_url" target="_blank" rel="noopener noreferrer">{{ item.public_url }}<ExternalLink :size="12" /></a></td>
          <td><div class="row-actions"><button class="icon-button" title="复制公开地址" @click="copyUrl(item)"><Copy :size="14" /></button><button class="icon-button" title="编辑" @click="open(item)"><Pencil :size="14" /></button><button class="icon-button danger-text" title="删除" @click="remove(item)"><Trash2 :size="14" /></button></div></td>
        </tr>
      </tbody>
    </table>
  </div>
  <div v-else class="empty"><div><AppWindow /><h2>还没有发布应用</h2><p>创建应用并绑定一个已启用的 Agent。</p></div></div>

  <div v-if="showForm" class="modal-backdrop" @click.self="showForm = false">
    <section class="modal" role="dialog" aria-modal="true" :aria-label="editing ? '编辑发布应用' : '新建发布应用'">
      <header><div><div class="eyebrow">APP CONFIG</div><h2>{{ editing ? '编辑发布应用' : '新建发布应用' }}</h2></div><button class="icon-button" title="关闭" @click="showForm = false"><X :size="17" /></button></header>
      <form class="form-grid" @submit.prevent="save">
        <div class="field"><label for="app-name">应用名称</label><input id="app-name" v-model.trim="form.name" required maxlength="80" /></div>
        <div class="field"><label for="app-slug">Slug</label><input id="app-slug" v-model.trim="form.slug" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" placeholder="fortune" /></div>
        <div class="field field--full"><label for="app-agent">绑定 Agent</label><select id="app-agent" v-model="form.agent_id" required><option disabled value="">请选择 Agent</option><option v-for="agent in agents" :key="agent.id" :value="agent.id" :disabled="!agent.enabled && agent.id !== form.agent_id">{{ agent.name }}{{ agent.enabled ? '' : '（已停用）' }}</option></select><div class="field-help">公开运行仍会在服务端强制禁用全部工具。</div></div>
        <div class="field"><label for="app-adapter">运行类型</label><select id="app-adapter" v-model="form.runtime_adapter" :disabled="builtinAdapterLocked"><option value="fortune">八字排盘</option><option value="dream">梦境解读</option></select></div>
        <div class="field"><label for="daily-limit">每日完整报告</label><input id="daily-limit" v-model.number="form.daily_limit" type="number" min="1" max="20" required /></div>
        <div class="field"><label for="ttl-hours">资料保存小时</label><input id="ttl-hours" v-model.number="form.ttl_hours" type="number" min="1" max="168" required /></div>
        <div class="field"><label for="max-questions">单次追问上限</label><input id="max-questions" v-model.number="form.max_questions" type="number" min="0" max="100" required /></div>
        <div class="field checkline"><input id="app-enabled" v-model="form.enabled" type="checkbox" /><label for="app-enabled">启用公开访问</label></div>
        <div class="field--full actions end"><button type="button" class="button button--secondary" @click="showForm = false">取消</button><button class="button" :disabled="loading">{{ loading ? '保存中...' : '保存应用' }}</button></div>
      </form>
    </section>
  </div>
</template>

<style scoped>
.app-table { min-width: 940px; }
.public-link { display: inline-flex; align-items: center; gap: 5px; max-width: 220px; color: var(--mint); font: 10px/1.5 ui-monospace, monospace; text-decoration: none; overflow-wrap: anywhere; }
.public-link:hover { text-decoration: underline; }
</style>
