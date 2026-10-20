import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/today' },
    { path: '/today', name: 'today', component: () => import('@/views/TodayView.vue') },
    { path: '/plan', name: 'plan', component: () => import('@/views/PlanView.vue') },
    { path: '/profile', name: 'profile', component: () => import('@/views/ProfileView.vue') },
    { path: '/log', name: 'log', component: () => import('@/views/LogView.vue') },
    { path: '/diet', name: 'diet', component: () => import('@/views/DietView.vue') },
    { path: '/shaping', name: 'shaping', component: () => import('@/views/ShapingView.vue') },
    { path: '/review', name: 'review', component: () => import('@/views/ReviewView.vue') },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

export default router
