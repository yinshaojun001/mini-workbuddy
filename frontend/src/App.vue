<script setup lang="ts">
import { Menu } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from '@/components/layout/AppSidebar.vue'

const route = useRoute()
const mobileOpen = ref(false)
</script>

<template>
  <div class="app-shell">
    <AppSidebar :open="mobileOpen" @close="mobileOpen = false" />
    <div class="app-main">
      <header class="mobile-header">
        <button class="icon-button" title="打开导航" @click="mobileOpen = true"><Menu :size="19" /></button>
        <span class="mobile-brand">MW / {{ route.meta.title }}</span>
      </header>
      <main class="page" :class="{ 'page--wide': route.meta.wide }">
        <RouterView />
      </main>
    </div>
  </div>
</template>

