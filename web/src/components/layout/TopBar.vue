<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNotice } from '@/composables/useNotice'
import AccountDialog from '@/components/account/AccountDialog.vue'
import DeleteAccountDialog from '@/components/account/DeleteAccountDialog.vue'
import BaseDialog from '@/components/common/BaseDialog.vue'
import ProfileView from '@/views/ProfileView.vue'
import { useProfileWindow } from '@/composables/useProfileWindow'
import NavIcon from './NavIcon.vue'
import { moduleTitle } from '@/utils/moduleNavigation'

defineEmits<{ menu: []; search: [] }>()
const auth = useAuthStore()
const route = useRoute()
const notice = useNotice()
const profileWindow = useProfileWindow()
const account = ref<InstanceType<typeof AccountDialog> | null>(null)
const profileDialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const profileContentMounted = ref(false)
const deleteAccountDialog = ref<InstanceType<typeof DeleteAccountDialog> | null>(null)
const avatar = ref('')
const profileMenuOpen = ref(false)
let closeTimer: number | null = null
const pageTitle = computed(() => moduleTitle(route))
const dateLabel = new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'short' }).format(new Date())
watch(() => auth.user?.id, (id) => {
  try { avatar.value = id ? localStorage.getItem(`fitnessCoachAvatar:${id}`) || '' : '' } catch { avatar.value = '' }
}, { immediate: true })
watch(profileWindow.open, async (isOpen) => {
  if (!isOpen) { profileDialog.value?.close(); return }
  profileContentMounted.value = true
  await nextTick()
  profileDialog.value?.open()
}, { immediate: true })
function showProfileMenu(): void {
  if (closeTimer !== null) window.clearTimeout(closeTimer)
  profileMenuOpen.value = true
}
function hideProfileMenu(): void {
  if (closeTimer !== null) window.clearTimeout(closeTimer)
  closeTimer = window.setTimeout(() => { profileMenuOpen.value = false }, 140)
}
function openUserData(): void { profileMenuOpen.value = false; void account.value?.open() }
async function openProfile(): Promise<void> {
  profileMenuOpen.value = false
  profileWindow.openProfileWindow()
}
function openDeleteAccount(): void { profileMenuOpen.value = false; void deleteAccountDialog.value?.open() }
async function logout(): Promise<void> {
  profileMenuOpen.value = false
  try { await auth.logout() }
  catch (error) { notice.notify(error instanceof Error ? error.message : '退出登录失败。', 'error') }
}
onBeforeUnmount(() => { if (closeTimer !== null) window.clearTimeout(closeTimer) })
</script>

<template>
  <header class="dashboard-topbar">
    <div class="topbar-title">
      <button class="mobile-menu" aria-label="打开导航" @click="$emit('menu')"><NavIcon name="menu" /></button>
      <div><h1>{{ pageTitle }}</h1></div>
    </div>
    <div class="topbar-actions">
      <span class="topbar-date">{{ dateLabel }}</span>
      <button class="topbar-search" @click="$emit('search')"><NavIcon name="search" /><span>搜索动作</span><kbd>Ctrl K</kbd></button>
      <div v-if="auth.isAuthenticated" class="topbar-profile-wrap" @pointerenter="showProfileMenu" @pointerleave="hideProfileMenu" @focusin="showProfileMenu" @focusout="hideProfileMenu" @keydown.escape="profileMenuOpen = false">
        <button class="user-menu-button topbar-profile-entry" type="button" aria-label="打开用户菜单" aria-haspopup="menu" :aria-expanded="profileMenuOpen" @click="profileMenuOpen = !profileMenuOpen">
          <span class="user-menu-avatar" :class="{ 'has-avatar-image': avatar }"><img v-if="avatar" :src="avatar" alt="" /><template v-else>{{ (auth.user?.display_name || auth.user?.username || '禾').slice(0, 1) }}</template></span>
          <span class="user-menu-text"><b>{{ auth.user?.display_name || auth.user?.username || '我的账号' }}</b></span>
          <svg class="topbar-profile-chevron" viewBox="0 0 20 20" aria-hidden="true"><path d="m6 8 4 4 4-4" /></svg>
        </button>
        <div v-if="profileMenuOpen" class="topbar-profile-menu" role="menu">
          <button type="button" role="menuitem" @click="openUserData"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3.5"/><path d="M5 20a7 7 0 0 1 14 0"/></svg><span><b>用户数据</b><small>体重、目标与身体变化</small></span></button>
          <button type="button" role="menuitem" @click="openProfile"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.4 1a8 8 0 0 0-1.8-1L14.4 3h-4L10 6a8 8 0 0 0-1.8 1L5.8 6 3.8 9.5 6 11a7 7 0 0 0 0 2l-2.2 1.5 2 3.5 2.4-1a8 8 0 0 0 1.8 1l.4 3h4l.4-3a8 8 0 0 0 1.8-1l2.4 1 2-3.5L19 13a7 7 0 0 0 .1-1Z"/></svg><span><b>档案与设计</b><small>管理身体档案和偏好</small></span></button>
          <button class="profile-menu-logout" type="button" role="menuitem" @click="logout"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 5H5v14h5M14 8l4 4-4 4M8 12h10"/></svg><span><b>退出登录</b><small>结束当前账号会话</small></span></button>
          <button class="profile-menu-logout" type="button" role="menuitem" @click="openDeleteAccount"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v5m4-5v5"/></svg><span><b>注销账号</b><small>永久删除账号及关联数据</small></span></button>
        </div>
      </div>
    </div>
    <DeleteAccountDialog ref="deleteAccountDialog" />
    <AccountDialog ref="account" @avatar-saved="avatar = $event" />
    <BaseDialog ref="profileDialog" class="user-dialog profile-settings-dialog" aria-labelledby="profile-settings-title" @close="profileWindow.closeProfileWindow()">
      <div class="user-dialog-top profile-settings-dialog-head"><div><p class="eyebrow">档案与设计</p><h2 id="profile-settings-title">个人身体档案</h2></div><button class="user-dialog-close" type="button" aria-label="关闭档案与设计" @click="profileDialog?.close()">×</button></div>
      <ProfileView v-if="profileContentMounted" embedded @close="profileWindow.closeProfileWindow()" />
    </BaseDialog>
  </header>
</template>
