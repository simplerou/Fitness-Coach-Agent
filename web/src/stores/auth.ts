import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { ApiError } from '@/api/client'
import { deleteAccount, getCurrentAccount, loginAccount, logoutAccount, registerAccount } from '@/api/auth'
import type { AuthUser, DeleteAccountPayload, LoginPayload, RegisterPayload } from '@/api/types'

const AUTH_CHANGE_KEY = 'fitnessCoachAuthChanged'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const initialized = ref(false)
  const sessionError = ref<string | null>(null)
  const isAuthenticated = computed(() => user.value !== null)

  async function initializeSession(): Promise<void> {
    sessionError.value = null
    try {
      const result = await getCurrentAccount()
      user.value = result.user
    } catch (error) {
      user.value = null
      if (!(error instanceof ApiError && error.status === 401)) {
        sessionError.value = error instanceof ApiError && error.status === null
          ? '连接服务器失败，请确认应用服务仍在运行。'
          : error instanceof Error
          ? error.message
          : '连接服务器失败，请确认应用服务仍在运行。'
      }
    } finally {
      initialized.value = true
    }
  }

  async function login(payload: LoginPayload): Promise<void> {
    const result = await loginAccount(payload)
    user.value = result.user
    sessionError.value = null
    broadcastAuthChange()
  }

  async function register(payload: RegisterPayload): Promise<void> {
    const result = await registerAccount(payload)
    user.value = result.user
    sessionError.value = null
    broadcastAuthChange()
  }

  async function logout(): Promise<void> {
    await logoutAccount()
    user.value = null
    broadcastAuthChange()
  }

  async function removeAccount(payload: DeleteAccountPayload): Promise<void> {
    const userId = user.value?.id
    await deleteAccount(payload)
    if (userId !== undefined) {
      for (const prefix of ['fitnessCoachAvatar', 'fitnessCoachProfilePromptSkipped', 'fitnessCoachHomeLayout']) {
        try { localStorage.removeItem(prefix + ':' + userId) } catch { /* Storage may be disabled. */ }
      }
    }
    user.value = null
    sessionError.value = null
    broadcastAuthChange()
  }

  function broadcastAuthChange(): void {
    try {
      localStorage.setItem(AUTH_CHANGE_KEY, String(Date.now()))
    } catch {
      // 当前标签页的登录状态仍会正常更新。
    }
  }

  function bindCrossTabSync(): () => void {
    const handleStorage = (event: StorageEvent): void => {
      if (event.key === AUTH_CHANGE_KEY) window.location.reload()
    }
    const previous = window.onstorage
    window.onstorage = handleStorage
    return () => { if (window.onstorage === handleStorage) window.onstorage = previous }
  }

  return {
    user,
    initialized,
    sessionError,
    isAuthenticated,
    initializeSession,
    login,
    register,
    logout,
    removeAccount,
    bindCrossTabSync,
  }
})
