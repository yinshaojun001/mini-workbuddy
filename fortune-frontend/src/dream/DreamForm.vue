<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'
import type { DreamPayload } from '@/types'

const props = defineProps<{
  emotions: string[]
  maxEmotions: number
  remaining: number
  loading: boolean
}>()
const emit = defineEmits<{ submit: [payload: DreamPayload] }>()
const showRecentContext = ref(false)

const form = reactive({
  dream_text: '',
  emotions: [] as string[],
  recurring: false,
  recent_context: '',
})

const dreamLength = computed(() => form.dream_text.trim().length)
const canSubmit = computed(() => !props.loading && props.remaining > 0 && dreamLength.value >= 20 && dreamLength.value <= 4000)

function toggleEmotion(value: string) {
  if (form.emotions.includes(value)) {
    form.emotions = form.emotions.filter((item) => item !== value)
    return
  }
  if (form.emotions.length < props.maxEmotions) form.emotions.push(value)
}

function submit() {
  if (!canSubmit.value) return
  emit('submit', {
    dream_text: form.dream_text.trim(),
    emotions: [...form.emotions],
    recurring: form.recurring,
    recent_context: form.recent_context.trim() || null,
  })
}
</script>

<template>
  <form class="birth-form dream-form" @submit.prevent="submit">
    <div class="form-intro">
      <div><span class="section-number">01</span><h2>记录梦境</h2></div>
      <span class="quota">今日剩余 {{ remaining }} 次</span>
    </div>

    <div class="field">
      <label for="dream-text">梦境正文 <small>{{ dreamLength }}/4000</small></label>
      <textarea id="dream-text" v-model="form.dream_text" class="dream-textarea" minlength="20" maxlength="4000" rows="8" :disabled="loading || remaining < 1" placeholder="写下梦里发生了什么、出现了谁、醒来时最强烈的感受" />
    </div>

    <div class="field">
      <span>主要情绪 <small>最多 {{ maxEmotions }} 个</small></span>
      <div class="emotion-grid">
        <button
          v-for="emotion in emotions"
          :key="emotion"
          type="button"
          :class="{ active: form.emotions.includes(emotion) }"
          :disabled="loading || (!form.emotions.includes(emotion) && form.emotions.length >= maxEmotions)"
          @click="toggleEmotion(emotion)"
        >
          {{ emotion }}
        </button>
      </div>
    </div>

    <label class="checkline dream-check"><input v-model="form.recurring" type="checkbox" :disabled="loading" />这是重复出现的梦</label>

    <button class="context-toggle" type="button" :aria-expanded="showRecentContext" aria-controls="recent-context-field" @click="showRecentContext = !showRecentContext">
      <component :is="showRecentContext ? ChevronUp : ChevronDown" :size="16" />
      {{ showRecentContext ? '收起近期背景' : '补充近期背景' }}
    </button>
    <div v-if="showRecentContext" id="recent-context-field" class="field">
      <label for="recent-context">近期背景 <small>可选，最多 500 字</small></label>
      <textarea id="recent-context" v-model="form.recent_context" class="dream-textarea compact" maxlength="500" rows="4" :disabled="loading" placeholder="可以补充最近的压力、变化或牵挂" />
    </div>

    <button class="primary-command" type="submit" :disabled="!canSubmit">{{ remaining < 1 ? '今日额度已用完' : '开始解梦' }}</button>
    <p class="privacy-line">梦境资料仅用于本次匿名会话，24 小时后清除</p>
  </form>
</template>
