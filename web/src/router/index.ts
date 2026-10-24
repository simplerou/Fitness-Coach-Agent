import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useProfileWindow } from '@/composables/useProfileWindow'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/today' },
    { path: '/admin/knowledge', name: 'admin-knowledge', meta: { requiresAdmin: true }, component: () => import('@/views/AdminKnowledgeView.vue') },
    { path: '/admin', name: 'admin', meta: { requiresAdmin: true }, component: () => import('@/views/AdminView.vue') },
    { path: '/today', name: 'today', component: () => import('@/views/TodayView.vue') },
    { path: '/plan', name: 'plan', component: () => import('@/views/PlanView.vue') },
    { path: '/profile', name: 'profile', component: () => import('@/views/ProfileView.vue') },
    { path: '/log', name: 'log', component: () => import('@/views/LogView.vue') },
    { path: '/diet', name: 'diet', component: () => import('@/views/DietView.vue') },
    { path: '/shaping', name: 'shaping', component: () => import('@/views/ShapingView.vue') },
    { path: '/review', name: 'review', component: () => import('@/views/ReviewView.vue') },
    { path: '/library', name: 'library', component: () => import('@/views/LibraryView.vue') },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

// 身体档案始终通过全局档案窗口打开；回到来源路由，避免渲染成长页面。
router.beforeEach(async (to, from) => {
  if (to.meta.requiresAdmin) {
    const auth = useAuthStore()
    if (!auth.initialized) await auth.initializeSession()
    if (!auth.isAdmin) return { name: 'today', replace: true }
  }
  if (to.name !== 'profile') return true
  useProfileWindow().openProfileWindow()
  if (from.name && from.name !== 'profile') return { path: from.fullPath, replace: true }
  return { name: 'today', replace: true }
})

export default router
