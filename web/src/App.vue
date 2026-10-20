<script setup lang="ts">
import { onBeforeUnmount, onMounted, watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import AuthGate from '@/components/auth/AuthGate.vue'
import NoticeModal from '@/components/common/NoticeModal.vue'
import TopBar from '@/components/layout/TopBar.vue'
import TabBar from '@/components/layout/TabBar.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import { useAuthStore } from '@/stores/auth'
import { useSafetyStore } from '@/stores/safety'
import { useProfileStore } from '@/stores/profile'
import { useShapingStore } from '@/stores/shaping'

const auth = useAuthStore()
const safety = useSafetyStore()
const profile = useProfileStore()
const shaping = useShapingStore()
const route = useRoute()
const router = useRouter()
let stopCrossTabSync: (() => void) | null = null
let screeningTimer: number | null = null
let onboardingCheckedFor: number | null = null
const previousVisibilityHandler = document.onvisibilitychange
document.onvisibilitychange = () => { if (!document.hidden) { safety.expireScreeningForNewDay(); shaping.refreshReminderDate() } }
watch(() => auth.isAuthenticated, (authenticated) => {
  document.body.classList.toggle('auth-open', !authenticated)
}, { immediate: true })
watch(() => [auth.initialized, auth.user?.id] as const, async ([initialized, userId]) => {
  if (!initialized || !userId || onboardingCheckedFor === userId) return
  onboardingCheckedFor = userId
  try {
    await profile.load()
    let skipped = false
    try { skipped = localStorage.getItem(`fitnessCoachProfilePromptSkipped:${userId}`) === 'true' } catch { /* storage may be disabled */ }
    if (!profile.profile && !skipped) await router.replace({ name: 'profile' })
  } catch { /* the profile page reports read errors */ }
})
watch(() => route.name, () => { safety.expireScreeningForNewDay(); shaping.refreshReminderDate() })
onMounted(() => {
  stopCrossTabSync = auth.bindCrossTabSync()
  void auth.initializeSession()
  screeningTimer = window.setInterval(() => safety.expireScreeningForNewDay(), 30_000)
})
onBeforeUnmount(() => {
  stopCrossTabSync?.()
  document.onvisibilitychange = previousVisibilityHandler
  if (screeningTimer !== null) window.clearInterval(screeningTimer)
  document.body.classList.remove('auth-open')
})
</script>

<template>
  <div class="shell">
    <TopBar />
    <main>
      <section class="intro">
        <p class="eyebrow">TRAIN WITH A LITTLE MORE CLARITY</p>
        <h1>让今天的训练，<em>有据可循。</em></h1>
        <p class="intro-copy">记录状态、查看训练安排。训练前先确认今天的身体感受。</p>
        <div class="demo-notice">
          <span>演示版本</span>
          身体档案、状态、训练记录和每周计划按账号分别保存在本机 PostgreSQL；服务重启或切换账号后需重新确认今天的身体状态。健康资料未做应用层加密，请勿公开部署或填写不愿保存在本机的数据。
        </div>
      </section>
      <template v-if="auth.isAuthenticated">
        <TabBar />
        <RouterView />
      </template>
    </main>
    <AppFooter />
    <AuthGate v-if="!auth.isAuthenticated" />
    <NoticeModal />
  </div>
</template>
