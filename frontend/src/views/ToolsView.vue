<script setup lang="ts">
import { FilePenLine, FileText, ShieldCheck, Terminal } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'
import type { Tool } from '@/types'
const items=ref<Tool[]>([]),error=ref('');const icons={read_file:FileText,write_file:FilePenLine,run_command:Terminal}
async function load(){try{items.value=await api('/api/tools')}catch(e){error.value=(e as Error).message}}
async function toggle(item:Tool){try{await api(`/api/tools/${item.id}`,{method:'PATCH',body:JSON.stringify({enabled:!item.enabled})});await load()}catch(e){error.value=(e as Error).message}}
onMounted(load)
</script>
<template><div class="page-heading"><div><div class="eyebrow">BUILT-IN TOOLS</div><h1>工具</h1><p class="subtitle">系统工具固定存在，只能调整全局启用状态。</p></div></div><div class="notice"><ShieldCheck :size="15"/>读文件可自动执行；写文件与命令行每次调用都需要你的明确审批。</div><div v-if="error" class="error">{{error}}</div><div class="tool-list"><article v-for="item in items" :key="item.id"><div class="tool-icon"><component :is="icons[item.id as keyof typeof icons]" :size="20"/></div><div><h2>{{item.name}}</h2><p>{{item.description}}</p><span class="badge" :class="item.approval_required?'badge--warn':'badge--ok'">{{item.approval_required?'每次需要审批':'工作区内自动执行'}}</span></div><button class="switch" :class="{on:item.enabled}" :aria-label="`${item.enabled?'停用':'启用'}${item.name}`" @click="toggle(item)"/></article></div></template>
<style scoped>.tool-list{display:grid;gap:10px}.tool-list article{min-height:106px;display:grid;grid-template-columns:44px 1fr auto;align-items:center;gap:14px;padding:16px;border:1px solid var(--line);background:white;border-radius:var(--radius)}.tool-icon{width:42px;height:42px;display:grid;place-items:center;background:#edf1ed;color:#37443c}.tool-list h2{font-size:13px;margin:0 0 4px}.tool-list p{font-size:11px;color:var(--muted);margin:0 0 8px}@media(max-width:600px){.tool-list article{grid-template-columns:40px 1fr}.tool-list .switch{grid-column:2}}</style>

