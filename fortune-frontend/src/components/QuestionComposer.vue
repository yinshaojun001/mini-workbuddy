<script setup lang="ts">
import { ref } from 'vue'
import { Send } from 'lucide-vue-next'
withDefaults(defineProps<{ remaining: number; disabled: boolean; inputId?: string; placeholder?: string }>(), {
  inputId: 'fortune-question',
  placeholder: '基于这份命盘继续提问',
})
const emit = defineEmits<{ submit: [content: string] }>()
const content = ref('')
function submit(){const value=content.value.trim();if(!value)return;emit('submit',value);content.value=''}
</script>
<template><form class="question-composer" @submit.prevent="submit"><div><label :for="inputId">继续追问</label><small>剩余 {{remaining}} 次</small></div><textarea :id="inputId" v-model="content" maxlength="500" rows="2" :disabled="disabled||remaining<1" :placeholder="placeholder" @keydown.enter.exact.prevent="submit"/><button type="submit" :disabled="disabled||remaining<1||!content.trim()" title="发送追问"><Send :size="18"/></button></form></template>
