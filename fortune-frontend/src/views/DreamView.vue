<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RotateCcw } from 'lucide-vue-next'
import PublicExperienceLayout from '@/layouts/PublicExperienceLayout.vue'
import DreamContext from '@/dream/DreamContext.vue'
import DreamForm from '@/dream/DreamForm.vue'
import DreamReport from '@/dream/DreamReport.vue'
import QuestionComposer from '@/components/QuestionComposer.vue'
import { createSession, deleteSession, getMetadata, getSession, streamRun } from '@/runtime/api'
import { forgetSessionId, readSessionId, rememberSessionId } from '@/runtime/session'
import type { AppState, DreamMetadata, DreamPayload, DreamSessionPayload, PublicMessage } from '@/types'

const APP_SLUG = 'dream'
const state = ref<AppState>('loading')
const metadata = ref<DreamMetadata | null>(null)
const current = ref<DreamSessionPayload | null>(null)
const report = ref('')
const pendingReply = ref('')
const error = ref('')
const dreamSketch = ref('')

function syncSession(payload: DreamSessionPayload) {
  current.value = payload
  report.value = payload.messages.find((item) => item.role === 'assistant')?.content || ''
  state.value = payload.session.status === 'report_ready' ? 'report_ready' : 'context_ready'
}

async function initialize() {
  try {
    metadata.value = await getMetadata<DreamMetadata>(APP_SLUG)
    const saved = readSessionId(APP_SLUG)
    if (saved) {
      try { syncSession(await getSession<DreamSessionPayload>(APP_SLUG, saved)); return } catch { forgetSessionId(APP_SLUG) }
    }
    state.value = 'form'
  } catch (reason) { error.value = (reason as Error).message; state.value = 'error' }
}

async function begin(payload: DreamPayload) {
  error.value = ''
  state.value = 'loading'
  try {
    const result = await createSession<DreamSessionPayload>(APP_SLUG, payload)
    dreamSketch.value = payload.dream_text
    current.value = result
    rememberSessionId(APP_SLUG, result.session.id)
    if (metadata.value && result.quota) metadata.value.quota = result.quota
    state.value = 'context_ready'
    await generateReport()
  } catch (reason) { error.value = (reason as Error).message; state.value = 'form' }
}

async function generateReport() {
  if (!current.value) return
  report.value = ''
  state.value = 'report_streaming'
  try {
    await streamRun(APP_SLUG, current.value.session.id, 'report', undefined, (event) => {
      if (event.type === 'message.delta') report.value += event.data.content || ''
      if (event.type === 'run.failed') throw new Error(event.data.message || '解梦生成失败')
    })
    syncSession(await getSession<DreamSessionPayload>(APP_SLUG, current.value.session.id))
  } catch (reason) { error.value = (reason as Error).message; state.value = 'context_ready' }
}

async function ask(content: string) {
  if (!current.value) return
  pendingReply.value = ''
  state.value = 'question_streaming'
  try {
    await streamRun(APP_SLUG, current.value.session.id, 'messages', content, (event) => {
      if (event.type === 'message.delta') pendingReply.value += event.data.content || ''
      if (event.type === 'run.failed') throw new Error(event.data.message || '追问失败')
    })
    syncSession(await getSession<DreamSessionPayload>(APP_SLUG, current.value.session.id))
    pendingReply.value = ''
  } catch (reason) { error.value = (reason as Error).message; state.value = 'report_ready' }
}

async function clearCurrent() {
  if (!current.value || !confirm('立即清除这份梦境资料和全部对话吗？')) return
  try { await deleteSession(APP_SLUG, current.value.session.id) } catch { /* already expired */ }
  forgetSessionId(APP_SLUG)
  current.value = null
  report.value = ''
  pendingReply.value = ''
  dreamSketch.value = ''
  state.value = 'form'
}

function completedQuestions(messages: PublicMessage[]) { return messages.slice(1) }
onMounted(initialize)
</script>

<template>
  <PublicExperienceLayout
    kind="dream"
    title="知梦"
    subtitle="传统梦象与自我反思"
    caption-kicker="DREAM SYMBOLS"
    :caption-lines="['以公版梦象作参照', '以现实感受作映照']"
    :meta="['梦境解读', '24 小时自动清除']"
    :show-clear="!!current"
    clear-label="清除梦境"
    clear-title="清除本次梦境"
    @clear="clearCurrent"
  >
    <div v-if="error" class="error-banner">{{ error }}<button title="关闭" @click="error = ''">×</button></div>
    <div v-if="state === 'loading' && !current" class="loading-state"><span>知</span><p>正在读取梦象资料</p></div>
    <DreamForm v-else-if="state === 'form' && metadata" :emotions="metadata.form.emotions.options" :max-emotions="metadata.form.emotions.max_items" :remaining="metadata.quota.remaining" :loading="false" @submit="begin" />
    <template v-else-if="current">
      <div class="report-topline"><div><span>梦境编号</span><b>{{ current.session.id.slice(0, 8) }}</b></div><div><span>资料到期</span><b>{{ new Date(current.session.expires_at).toLocaleString('zh-CN', { hour12: false }) }}</b></div><button v-if="state === 'context_ready'" class="retry-command" @click="generateReport"><RotateCcw :size="14" />生成解读</button></div>
      <DreamContext :context="current.context" :dream-text="dreamSketch" />
      <DreamReport :content="report" :streaming="state === 'report_streaming'" />
      <section v-if="current.messages.length > 1" class="followups"><h2>追问记录</h2><article v-for="message in completedQuestions(current.messages)" :key="message.id" :class="message.role"><label>{{ message.role === 'user' ? '你' : '知梦' }}</label><p>{{ message.content }}</p></article></section>
      <article v-if="pendingReply" class="pending-reply"><label>知梦</label><p>{{ pendingReply }}</p></article>
      <QuestionComposer v-if="state === 'report_ready' || state === 'question_streaming'" input-id="dream-question" placeholder="基于这场梦继续提问" :remaining="current.session.remaining_questions" :disabled="state === 'question_streaming'" @submit="ask" />
    </template>
  </PublicExperienceLayout>
</template>
