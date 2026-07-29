<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RotateCcw } from 'lucide-vue-next'
import PublicExperienceLayout from '@/layouts/PublicExperienceLayout.vue'
import BirthForm from '@/components/BirthForm.vue'
import BaziChart from '@/components/BaziChart.vue'
import ReadingReport from '@/components/ReadingReport.vue'
import QuestionComposer from '@/components/QuestionComposer.vue'
import { createSession, deleteSession, getMetadata, getSession, streamRun } from '@/runtime/api'
import { forgetSessionId, readSessionId, rememberSessionId } from '@/runtime/session'
import type { AppState, BirthPayload, FortuneChart, FortuneMetadata, FortuneSessionPayload, PublicMessage, SessionPayload } from '@/types'

const APP_SLUG = 'fortune'
const state = ref<AppState>('loading')
const metadata = ref<FortuneMetadata | null>(null)
const current = ref<FortuneSessionPayload | null>(null)
const report = ref('')
const pendingReply = ref('')
const error = ref('')

function normalizeFortuneSession(payload: SessionPayload): FortuneSessionPayload {
  const chart = (payload.context ?? (payload as Partial<FortuneSessionPayload>).chart) as FortuneChart
  return { ...payload, chart }
}

function syncSession(payload: SessionPayload) {
  current.value = normalizeFortuneSession(payload)
  report.value = payload.messages.find((item) => item.role === 'assistant')?.content || ''
  state.value = payload.session.status === 'report_ready' ? 'report_ready' : 'chart_ready'
}

async function initialize() {
  try {
    metadata.value = await getMetadata<FortuneMetadata>(APP_SLUG)
    const saved = readSessionId(APP_SLUG)
    if (saved) {
      try { syncSession(await getSession(APP_SLUG, saved)); return } catch { forgetSessionId(APP_SLUG) }
    }
    state.value = 'form'
  } catch (reason) { error.value = (reason as Error).message; state.value = 'error' }
}

async function begin(payload: BirthPayload) {
  error.value = ''
  state.value = 'loading'
  try {
    const result = await createSession<FortuneSessionPayload>(APP_SLUG, payload)
    current.value = normalizeFortuneSession(result)
    rememberSessionId(APP_SLUG, result.session.id)
    if (metadata.value && result.quota) metadata.value.quota = result.quota
    state.value = 'chart_ready'
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
      if (event.type === 'run.failed') throw new Error(event.data.message || '解读生成失败')
    })
    syncSession(await getSession(APP_SLUG, current.value.session.id))
  } catch (reason) { error.value = (reason as Error).message; state.value = 'chart_ready' }
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
    syncSession(await getSession(APP_SLUG, current.value.session.id))
    pendingReply.value = ''
  } catch (reason) { error.value = (reason as Error).message; state.value = 'report_ready' }
}

async function clearCurrent() {
  if (!current.value || !confirm('立即清除这份命盘、出生资料和全部对话吗？')) return
  try { await deleteSession(APP_SLUG, current.value.session.id) } catch { /* already expired */ }
  forgetSessionId(APP_SLUG)
  current.value = null
  report.value = ''
  pendingReply.value = ''
  state.value = 'form'
}

function completedQuestions(messages: PublicMessage[]) { return messages.slice(1) }
onMounted(initialize)
</script>

<template>
  <PublicExperienceLayout
    kind="fortune"
    title="知命"
    subtitle="四柱命理文化解读"
    caption-kicker="FOUR PILLARS"
    :caption-lines="['以确定性排盘为依据', '以克制语言作解释']"
    :meta="['公历排盘', '24 小时自动清除']"
    :show-clear="!!current"
    clear-label="清除资料"
    clear-title="清除本次资料"
    @clear="clearCurrent"
  >
    <div v-if="error" class="error-banner">{{ error }}<button title="关闭" @click="error = ''">×</button></div>
    <div v-if="state === 'loading' && !current" class="loading-state"><span>知</span><p>正在读取历书数据</p></div>
    <BirthForm v-else-if="state === 'form' && metadata" :locations="metadata.locations" :remaining="metadata.quota.remaining" :loading="false" @submit="begin" />
    <template v-else-if="current">
      <div class="report-topline"><div><span>命盘编号</span><b>{{ current.session.id.slice(0, 8) }}</b></div><div><span>资料到期</span><b>{{ new Date(current.session.expires_at).toLocaleString('zh-CN', { hour12: false }) }}</b></div><button v-if="state === 'chart_ready'" class="retry-command" @click="generateReport"><RotateCcw :size="14" />生成解读</button></div>
      <BaziChart :chart="current.chart" />
      <ReadingReport :content="report" :streaming="state === 'report_streaming'" />
      <section v-if="current.messages.length > 1" class="followups"><h2>追问记录</h2><article v-for="message in completedQuestions(current.messages)" :key="message.id" :class="message.role"><label>{{ message.role === 'user' ? '你' : '知命' }}</label><p>{{ message.content }}</p></article></section>
      <article v-if="pendingReply" class="pending-reply"><label>知命</label><p>{{ pendingReply }}</p></article>
      <QuestionComposer v-if="state === 'report_ready' || state === 'question_streaming'" :remaining="current.session.remaining_questions" :disabled="state === 'question_streaming'" @submit="ask" />
    </template>
  </PublicExperienceLayout>
</template>
