<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { CalendarDays, Clock3, MapPin } from 'lucide-vue-next'
import type { BirthPayload, Location } from '@/types'

const props = defineProps<{ locations: Location[]; remaining: number; loading: boolean }>()
const emit = defineEmits<{ submit: [payload: BirthPayload] }>()
const topics = [{ id: 'career', label: '事业' }, { id: 'wealth', label: '财务' }, { id: 'relationship', label: '关系' }, { id: 'growth', label: '成长' }, { id: 'current_year', label: '流年' }]
const provinces = computed(() => props.locations.filter((item) => item.level === 'province'))
const cities = computed(() => props.locations.filter((item) => item.level === 'city' && item.parent_code === form.province_code))
const form = reactive<BirthPayload>({ name: null, gender: 'female', birth_date: '', birth_time: '12:00', birth_time_unknown: false, province_code: '', city_code: '', true_solar_time: false, focus_topics: [] })
const today = new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Shanghai' })

watch(provinces, (items) => { if (!form.province_code && items[0]) form.province_code = items[0].code }, { immediate: true })
watch(cities, (items) => { if (!items.some((item) => item.code === form.city_code)) form.city_code = items[0]?.code || '' }, { immediate: true })
watch(() => form.birth_time_unknown, (unknown) => { form.birth_time = unknown ? null : '12:00'; if (unknown) form.true_solar_time = false })

function toggleTopic(id: string) {
  const index = form.focus_topics.indexOf(id)
  if (index >= 0) form.focus_topics.splice(index, 1)
  else if (form.focus_topics.length < 3) form.focus_topics.push(id)
}
function submit() { emit('submit', { ...form, name: form.name || null, focus_topics: [...form.focus_topics] }) }
</script>

<template>
  <form class="birth-form" @submit.prevent="submit">
    <div class="form-intro"><div><span class="section-number">01</span><h2>出生信息</h2></div><span class="quota">今日剩余 {{ remaining }} 次</span></div>
    <div class="field"><label>性别</label><div class="segmented"><button type="button" :class="{ active: form.gender === 'female' }" @click="form.gender = 'female'">女</button><button type="button" :class="{ active: form.gender === 'male' }" @click="form.gender = 'male'">男</button></div></div>
    <div class="field-grid">
      <label class="field"><span><CalendarDays :size="15" />公历出生日期</span><input v-model="form.birth_date" type="date" min="1900-01-01" :max="today" required /></label>
      <label class="field"><span><Clock3 :size="15" />出生时间</span><input v-model="form.birth_time" type="time" :disabled="form.birth_time_unknown" :required="!form.birth_time_unknown" /></label>
    </div>
    <label class="checkline"><input v-model="form.birth_time_unknown" type="checkbox" /><span>时辰不详</span></label>
    <div class="field-grid">
      <label class="field"><span><MapPin :size="15" />省份</span><select v-model="form.province_code" required><option v-for="item in provinces" :key="item.code" :value="item.code">{{ item.name }}</option></select></label>
      <label class="field"><span>城市</span><select v-model="form.city_code" required><option v-for="item in cities" :key="item.code" :value="item.code">{{ item.name }}</option></select></label>
    </div>
    <label class="toggleline" :class="{ disabled: form.birth_time_unknown }"><span><b>真太阳时校正</b><small>按城市经度修正当地太阳时</small></span><input v-model="form.true_solar_time" type="checkbox" :disabled="form.birth_time_unknown" /></label>
    <div class="field"><label>关注方向 <small>最多三项</small></label><div class="topic-grid"><button v-for="topic in topics" :key="topic.id" type="button" :class="{ active: form.focus_topics.includes(topic.id) }" @click="toggleTopic(topic.id)">{{ topic.label }}</button></div></div>
    <label class="field"><span>昵称 <small>可选</small></span><input v-model.trim="form.name" maxlength="30" placeholder="如何称呼你" /></label>
    <button class="primary-command" :disabled="loading || remaining < 1">{{ loading ? '正在排盘…' : remaining < 1 ? '今日额度已用完' : '开始排盘' }}</button>
    <p class="privacy-line">出生资料仅用于本次解读，24 小时后自动清除。</p>
  </form>
</template>
