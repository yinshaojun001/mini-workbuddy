import { createRouter, createWebHistory, type RouterHistory, type RouteRecordRaw } from 'vue-router'

export const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/fortune' },
  { path: '/fortune', component: () => import('@/views/FortuneView.vue') },
  { path: '/dream', component: () => import('@/views/DreamView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/fortune' },
]

export function createPublicRouter(history: RouterHistory) {
  return createRouter({ history, routes })
}

export const router = createPublicRouter(createWebHistory())
