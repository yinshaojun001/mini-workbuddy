import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { title: '工作台' } },
    { path: '/agents', name: 'agents', component: () => import('@/views/AgentsView.vue'), meta: { title: '智能体' } },
    { path: '/agents/new', name: 'agent-new', component: () => import('@/views/AgentEditorView.vue'), meta: { title: '新建智能体' } },
    { path: '/agents/:id/edit', name: 'agent-edit', component: () => import('@/views/AgentEditorView.vue'), meta: { title: '编辑智能体' } },
    { path: '/agents/:id/run', name: 'agent-run', component: () => import('@/views/AgentRunView.vue'), meta: { title: '运行智能体', wide: true } },
    { path: '/models', name: 'models', component: () => import('@/views/ModelsView.vue'), meta: { title: '模型' } },
    { path: '/skills', name: 'skills', component: () => import('@/views/SkillsView.vue'), meta: { title: '技能' } },
    { path: '/tools', name: 'tools', component: () => import('@/views/ToolsView.vue'), meta: { title: '工具' } },
    { path: '/apps', name: 'apps', component: () => import('@/views/AppsView.vue'), meta: { title: '发布应用' } },
    { path: '/public-runs', name: 'public-runs', component: () => import('@/views/PublicRunsView.vue'), meta: { title: '公开运行', wide: true } },
    { path: '/runs', name: 'runs', component: () => import('@/views/RunsView.vue'), meta: { title: '运行记录' } },
  ],
})

router.afterEach((to) => { document.title = `${String(to.meta.title || '工作台')} · Mini-workbuddy` })

export default router
