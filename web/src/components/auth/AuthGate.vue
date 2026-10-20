<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ApiError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

type AuthMode = 'login' | 'register'
type PasswordField = 'password' | 'password_confirm'

const auth = useAuthStore()
const mode = ref<AuthMode>('login')
const loading = ref(false)
const formError = ref('')
const usernameError = ref('')
const confirmError = ref('')
const usernameInput = ref<HTMLInputElement | null>(null)
const passwordInput = ref<HTMLInputElement | null>(null)
const confirmInput = ref<HTMLInputElement | null>(null)
const visible = reactive<Record<PasswordField, boolean>>({
  password: false,
  password_confirm: false,
})
const fields = reactive({ username: '', display_name: '', password: '', password_confirm: '' })
const isRegister = computed(() => mode.value === 'register')
const title = computed(() => isRegister.value ? '创建你的训练账号' : '欢迎回来')
const description = computed(() => isRegister.value
  ? '注册后会为你单独保存档案、训练计划和记录。'
  : '登录后查看你自己的身体档案、训练计划和记录。')
const submitLabel = computed(() => loading.value
  ? (isRegister.value ? '正在注册…' : '正在登录…')
  : (isRegister.value ? '注册并进入' : '登录'))

watch(() => auth.sessionError, (value) => {
  if (value) formError.value = value
}, { immediate: true })

function clearErrors(): void {
  formError.value = ''
  usernameError.value = ''
}

function setMode(nextMode: AuthMode): void {
  if (mode.value === nextMode) return
  mode.value = nextMode
  fields.username = ''
  fields.display_name = ''
  fields.password = ''
  fields.password_confirm = ''
  visible.password = false
  visible.password_confirm = false
  clearErrors()
  confirmError.value = ''
}

function validateConfirmPassword(allowEmpty = false): boolean {
  const password = fields.password.trim()
  const confirmation = fields.password_confirm.trim()
  if (!confirmation) {
    confirmError.value = allowEmpty ? '请再次输入密码。' : ''
    return !allowEmpty
  }
  if (password !== confirmation) {
    confirmError.value = '两次输入的密码不一致，请重新确认。'
    return false
  }
  confirmError.value = ''
  return true
}

function failureMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return error instanceof Error ? error.message : '暂时无法完成请求，请稍后重试。'
  }
  if (error.status === 401) return '账号或密码不正确，请检查后重试。'
  if (error.status === 429) return '尝试次数过多，请稍后再试。'
  if (error.status === 403 || error.status === 423) return '账号当前暂不可用，请稍后重试或联系管理员。'
  if (error.status === 409) return error.message
  if (error.status === 422) return '输入内容不符合要求，请检查后重试。'
  if (error.status === null || error.status >= 500) return '网络或服务暂时异常，请稍后重试。'
  return error.message || '暂时无法完成请求，请稍后重试。'
}

async function submit(): Promise<void> {
  clearErrors()
  if (!fields.username.trim()) {
    usernameError.value = '请填写用户名。'
    usernameInput.value?.focus()
    return
  }
  if (!fields.password || (isRegister.value && !fields.password.trim())) {
    formError.value = '请填写密码。'
    passwordInput.value?.focus()
    return
  }
  if (isRegister.value && !fields.password_confirm.trim()) {
    confirmError.value = '请再次输入密码。'
    formError.value = '请再次输入密码后继续注册。'
    confirmInput.value?.focus()
    return
  }
  if (isRegister.value && !validateConfirmPassword(true)) {
    formError.value = '两次输入的密码不一致，请重新确认。'
    confirmInput.value?.focus()
    return
  }
  if (isRegister.value && fields.password.length < 8) {
    formError.value = '注册密码至少需要 8 位。'
    passwordInput.value?.focus()
    return
  }

  loading.value = true
  try {
    if (isRegister.value) {
      await auth.register({
        username: fields.username.trim(),
        password: fields.password,
        display_name: fields.display_name.trim() || null,
      })
    } else {
      await auth.login({ username: fields.username.trim(), password: fields.password })
    }
  } catch (error) {
    formError.value = failureMessage(error)
  } finally {
    loading.value = false
  }
}

function clearPasswordErrors(field: PasswordField): void {
  formError.value = ''
  if (confirmError.value) validateConfirmPassword()
  else if (field === 'password') confirmError.value = ''
}
</script>

<template>
  <div class="modal-backdrop auth-backdrop" role="presentation">
    <section class="auth-modal" role="dialog" aria-modal="true" aria-labelledby="auth-title" aria-describedby="auth-description">
      <div class="auth-brand-mark" aria-hidden="true">禾</div>
      <p class="eyebrow">FITNESS COACH</p>
      <h2 id="auth-title">{{ title }}</h2>
      <p id="auth-description" class="auth-description">{{ description }}</p>

      <form class="form-stack" novalidate @submit.prevent="submit">
        <label class="field">
          <span>用户名</span>
          <input
            ref="usernameInput"
            v-model="fields.username"
            :class="{ 'input-error': usernameError }"
            :aria-invalid="Boolean(usernameError)"
            name="username"
            type="text"
            required
            minlength="3"
            maxlength="24"
            autocomplete="username"
            pattern="[A-Za-z0-9_.-]+"
            placeholder="3–24 位字母、数字或 . _ -"
            @input="clearErrors"
          />
          <span v-if="usernameError" class="auth-inline-error" role="alert">{{ usernameError }}</span>
        </label>

        <label v-if="isRegister" class="field">
          <span>昵称（选填）</span>
          <input v-model="fields.display_name" name="display_name" type="text" maxlength="32" autocomplete="nickname" placeholder="在“我的”页面显示" />
        </label>

        <label class="field">
          <span>密码</span>
          <span class="password-input-wrap">
            <input
              ref="passwordInput"
              v-model="fields.password"
              name="password"
              :type="visible.password ? 'text' : 'password'"
              required
              minlength="8"
              maxlength="128"
              :autocomplete="isRegister ? 'new-password' : 'current-password'"
              placeholder="至少 8 位"
              @input="clearPasswordErrors('password')"
            />
            <button class="password-toggle" type="button" :aria-label="visible.password ? '隐藏密码' : '显示密码'" :aria-pressed="visible.password" :title="visible.password ? '隐藏密码' : '显示密码'" @mousedown.prevent @click="visible.password = !visible.password">
              <svg v-if="visible.password" viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>
              <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="m3 3 18 18M10.6 10.6a2 2 0 0 0 2.8 2.8M9.9 5.2A10.7 10.7 0 0 1 12 5c6.4 0 10 7 10 7s-3.6 7-10 7c-1.4 0-2.6-.3-3.7-.8"/></svg>
            </button>
          </span>
        </label>

        <label v-if="isRegister" class="field">
          <span>确认密码</span>
          <span class="password-input-wrap">
            <input
              ref="confirmInput"
              v-model="fields.password_confirm"
              :class="{ 'input-error': confirmError }"
              :aria-invalid="Boolean(confirmError)"
              name="password_confirm"
              :type="visible.password_confirm ? 'text' : 'password'"
              minlength="8"
              maxlength="128"
              autocomplete="new-password"
              placeholder="再输入一次密码"
              @input="clearPasswordErrors('password_confirm')"
              @blur="isRegister && fields.password.trim() && validateConfirmPassword(true)"
            />
            <button class="password-toggle" type="button" :aria-label="visible.password_confirm ? '隐藏密码' : '显示密码'" :aria-pressed="visible.password_confirm" :title="visible.password_confirm ? '隐藏密码' : '显示密码'" @mousedown.prevent @click="visible.password_confirm = !visible.password_confirm">
              <svg v-if="visible.password_confirm" viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>
              <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="m3 3 18 18M10.6 10.6a2 2 0 0 0 2.8 2.8M9.9 5.2A10.7 10.7 0 0 1 12 5c6.4 0 10 7 10 7s-3.6 7-10 7c-1.4 0-2.6-.3-3.7-.8"/></svg>
            </button>
          </span>
          <span v-if="confirmError" class="auth-inline-error" role="alert">{{ confirmError }}</span>
        </label>

        <p v-if="formError" class="auth-error" role="alert" aria-live="assertive">{{ formError }}</p>
        <p v-else class="auth-error" aria-hidden="true"></p>
        <button class="button button-primary auth-submit" type="submit" :disabled="loading" :aria-busy="loading">{{ submitLabel }}</button>
      </form>

      <div class="auth-mode-switch">
        <p v-if="!isRegister">没有账号？<button type="button" @click="setMode('register')">前往注册</button></p>
        <p v-else>已经有账号？<button type="button" @click="setMode('login')">前往登录</button></p>
      </div>
      <p class="fine-print">本机演示账号。密码以不可逆散列形式保存；忘记密码时目前需由管理员处理数据库账号。</p>
    </section>
  </div>
</template>
