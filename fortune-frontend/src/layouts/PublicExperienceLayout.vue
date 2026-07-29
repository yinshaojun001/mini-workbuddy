<script setup lang="ts">
import { Trash2 } from 'lucide-vue-next'
import PrivacyNotice from '@/components/PrivacyNotice.vue'
import type { PublicAppSlug } from '@/types'

defineProps<{
  kind: PublicAppSlug
  title: string
  subtitle: string
  captionKicker: string
  captionLines: string[]
  meta: string[]
  showClear: boolean
  clearLabel: string
  clearTitle: string
}>()

defineEmits<{ clear: [] }>()
</script>

<template>
  <div class="site-shell" :class="`site-shell-${kind}`">
    <aside class="almanac-rail">
      <div class="rail-brand"><span>知</span><div><b>{{ title }}</b><small>{{ subtitle }}</small></div></div>
      <nav class="app-switcher" aria-label="公开应用">
        <RouterLink to="/fortune" class="app-tab">知命</RouterLink>
        <span class="app-tab disabled" aria-disabled="true">知梦</span>
      </nav>
      <div class="rail-caption"><span>{{ captionKicker }}</span><p><template v-for="line in captionLines" :key="line">{{ line }}<br /></template></p></div>
    </aside>
    <main>
      <header class="topbar">
        <RouterLink :to="`/${kind}`" class="mobile-brand"><span>知</span><b>{{ title }}</b></RouterLink>
        <div class="mobile-switcher"><RouterLink to="/fortune">知命</RouterLink><span aria-disabled="true">知梦</span></div>
        <div class="top-meta"><span v-for="item in meta" :key="item">{{ item }}</span></div>
        <button v-if="showClear" class="clear-command" :title="clearTitle" @click="$emit('clear')"><Trash2 :size="15" />{{ clearLabel }}</button>
      </header>
      <div class="content-wrap">
        <slot />
        <PrivacyNotice :kind="kind" />
      </div>
    </main>
  </div>
</template>
