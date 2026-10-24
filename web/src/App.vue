<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import AuthGate from '@/components/auth/AuthGate.vue'
import LandingView from '@/views/LandingView.vue'
import NoticeModal from '@/components/common/NoticeModal.vue'
import TopBar from '@/components/layout/TopBar.vue'
import TabBar from '@/components/layout/TabBar.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import CommandPalette from '@/components/ui/CommandPalette.vue'
import CoachFloatingWindow from '@/components/coach/CoachFloatingWindow.vue'
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
let onboardingCheckedFor: number | null = null
const sidebarOpen = ref(false)
const authMode = ref<'login' | 'register' | null>(null)
const previousVisibilityHandler = document.onvisibilitychange
document.onvisibilitychange = () => { if (!document.hidden) { if (auth.isAuthenticated) void safety.refreshToday(); shaping.refreshReminderDate() } }
watch(() => auth.isAuthenticated, (authenticated) => {
  if (authenticated) {
    authMode.value = null
    if (auth.isAdmin && !route.meta.requiresAdmin) void router.replace({ name: 'admin' })
  }
})
watch(authMode, (mode) => {
  document.body.classList.toggle('auth-open', mode !== null)
})
watch(() => [auth.initialized, auth.user?.id] as const, async ([initialized, userId]) => {
  if (!initialized || !userId || auth.isAdmin || onboardingCheckedFor === userId) return
  onboardingCheckedFor = userId
  try {
    await profile.load()
    let skipped = false
    try { skipped = localStorage.getItem(`fitnessCoachProfilePromptSkipped:${userId}`) === 'true' } catch { /* storage may be disabled */ }
    if (!profile.profile && !skipped) await router.replace({ name: 'profile' })
  } catch { /* the profile page reports read errors */ }
})
watch(() => route.name, () => { if (auth.isAuthenticated) void safety.refreshToday(); shaping.refreshReminderDate() })
onMounted(() => {
  stopCrossTabSync = auth.bindCrossTabSync()
  if (!auth.initialized) void auth.initializeSession()
})
onBeforeUnmount(() => {
  stopCrossTabSync?.()
  document.onvisibilitychange = previousVisibilityHandler
  document.body.classList.remove('auth-open')
})
</script>

<template>
  <div :class="auth.isAuthenticated ? 'app-frame' : 'public-frame'">
    <template v-if="auth.isAuthenticated">
      <AppSidebar :open="sidebarOpen" @close="sidebarOpen = false" />
      <div class="app-workspace">
        <CommandPalette v-slot="{ open }">
          <TopBar @menu="sidebarOpen = true" @search="open()" />
        </CommandPalette>
        <main class="dashboard-content"><RouterView /><AppFooter /></main>
      </div>
      <TabBar />
      <CoachFloatingWindow />
    </template>
    <template v-if="!auth.isAuthenticated">
      <LandingView @authenticate="authMode = $event" />
      <AuthGate v-if="authMode" :initial-mode="authMode" @close="authMode = null" />
    </template>
    <NoticeModal />
  </div>
</template>
