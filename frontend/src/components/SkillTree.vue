<script setup lang="ts">
import { ChevronRight, FileText, Folder } from 'lucide-vue-next'
import type { TreeNode } from '@/types'
defineProps<{ nodes: TreeNode[] }>()
</script>
<template><ul class="tree"><li v-for="node in nodes" :key="node.path"><div class="tree-row"><ChevronRight v-if="node.type==='directory'" :size="12"/><span v-else class="indent"/><component :is="node.type==='directory'?Folder:FileText" :size="14"/><span>{{node.name}}</span></div><SkillTree v-if="node.children?.length" :nodes="node.children"/></li></ul></template>
<style scoped>.tree{list-style:none;padding:0;margin:0;font:11px/1.5 ui-monospace,monospace}.tree .tree{padding-left:20px}.tree-row{height:30px;display:flex;align-items:center;gap:6px;border-bottom:1px solid #edf0ed}.indent{width:12px}</style>

