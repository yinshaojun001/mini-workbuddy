<script setup lang="ts">
import { AppWindow, Bot, Boxes, Gauge, History, RadioTower, Wrench, X, Zap } from 'lucide-vue-next'

defineProps<{ open: boolean }>()
defineEmits<{ close: [] }>()

const links = [
  { to: '/', label: '工作台', icon: Gauge },
  { to: '/agents', label: '智能体', icon: Bot },
  { to: '/models', label: '模型', icon: Zap },
  { to: '/skills', label: '技能', icon: Boxes },
  { to: '/tools', label: '工具', icon: Wrench },
  { to: '/apps', label: '发布应用', icon: AppWindow },
  { to: '/public-runs', label: '公开运行', icon: RadioTower },
  { to: '/runs', label: '运行记录', icon: History },
]
</script>

<template>
  <div class="sidebar-backdrop" :class="{ visible: open }" @click="$emit('close')" />
  <aside class="sidebar" :class="{ open }">
    <div class="brand-row">
      <RouterLink class="brand" to="/" @click="$emit('close')"><span class="brand-mark">MW</span><span>Mini-workbuddy</span></RouterLink>
      <button class="icon-button sidebar-close" title="关闭导航" @click="$emit('close')"><X :size="18" /></button>
    </div>
    <p class="sidebar-label">本地智能体工作区</p>
    <nav class="sidebar-nav" aria-label="主导航">
      <RouterLink v-for="link in links" :key="link.to" :to="link.to" @click="$emit('close')">
        <component :is="link.icon" :size="18" /><span>{{ link.label }}</span>
      </RouterLink>
    </nav>
    <div class="sidebar-foot"><span class="status-dot" />本地服务</div>
  </aside>
</template>
