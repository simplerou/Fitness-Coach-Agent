<script setup lang="ts">
import { nextTick, ref } from 'vue'
import BaseDialog from '@/components/common/BaseDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useNotice } from '@/composables/useNotice'

const auth = useAuthStore()
const notice = useNotice()
const dialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const passwordInput = ref<HTMLInputElement | null>(null)
const password = ref('')
const confirmation = ref('')
const busy = ref(false)
const error = ref('')
function reset(): void {
  password.value = ''
  confirmation.value = ''
  error.value = ''
}
async function open(): Promise<void> {
  if (busy.value) return
  reset()
  dialog.value?.open()
  await nextTick()
  passwordInput.value?.focus()
}
async function submit(): Promise<void> {
  if (busy.value || !password.value || confirmation.value !== '注销账号') return
  busy.value = true
  error.value = ''
  try {
    await auth.removeAccount({ password: password.value, confirmation: '注销账号' })
    dialog.value?.close()
    reset()
    notice.notify('账号已注销，账号及关联数据已删除。', 'success')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '注销失败，账号未删除，请稍后重试。'
    password.value = ''
    await nextTick()
    passwordInput.value?.focus()
  } finally {
    busy.value = false
  }
}
defineExpose({ open })
</script>

<template>
  <BaseDialog ref="dialog" class="user-dialog delete-account-dialog" :dismissible="!busy"
    aria-labelledby="delete-account-title" aria-describedby="delete-account-description" @close="reset">
    <div class="delete-account-heading">
      <h2 id="delete-account-title">确定注销账号？</h2>
      <button class="delete-account-close" type="button" :disabled="busy" aria-label="取消注销账号" @click="dialog?.close()">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg>
      </button>
    </div>
    <p id="delete-account-description">你正在注销账号 <strong>{{ auth.user?.username }}</strong>。此操作无法撤销，请确认已保存需要保留的资料。</p>
    <div class="delete-account-warning"><b>以下账号数据将永久删除</b><ul>
      <li>身体档案、体重、围度、体成分与对比照片</li>
      <li>训练计划、训练记录、恢复打卡和进阶建议</li>
      <li>饮食档案、餐食、饮水、规划记录与报告</li>
      <li>教练问答记录、待确认草案及账号偏好</li>
    </ul><p>注销后会退出登录，其他设备上的该账号也将无法继续访问。其他账号的数据不受影响。</p></div>
    <form class="form-stack" @submit.prevent="submit">
      <label class="field"><span>当前密码</span><input ref="passwordInput" v-model="password" name="delete-account-password" type="password" autocomplete="current-password" required maxlength="128" :disabled="busy" /></label>
      <label class="field"><span>请输入“注销账号”以确认</span><input v-model="confirmation" name="delete-account-confirmation" type="text" autocomplete="off" required maxlength="4" :disabled="busy" /></label>
      <p v-if="error" class="delete-account-error" role="alert">{{ error }}</p>
      <p v-if="busy" role="status">正在注销，请等待完成；提交后无法取消。</p>
      <div class="delete-account-actions"><button class="button button-quiet" type="button" :disabled="busy" @click="dialog?.close()">保留账号</button><button class="button button-danger" type="submit" :disabled="busy || !password || confirmation !== '注销账号'" :aria-busy="busy">{{ busy ? '正在注销…' : '永久注销账号' }}</button></div>
    </form>
  </BaseDialog>
</template>

<style scoped>
.delete-account-dialog{width:min(520px,calc(100vw - 28px));max-height:90dvh;overflow-y:auto;padding:24px}
.delete-account-heading{display:flex;align-items:center;justify-content:space-between;gap:16px}
.delete-account-heading h2{margin:0;font-size:var(--fs-xl)}
.delete-account-close{display:grid;place-items:center;width:44px;height:44px;padding:0;border:0;border-radius:var(--r-sm);background:var(--surface-2);color:var(--text-2);cursor:pointer}
.delete-account-close svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.7}
.delete-account-dialog>p{font-size:var(--fs-base);color:var(--text-2);overflow-wrap:anywhere}
.delete-account-warning{margin:20px 0;padding:16px;border-radius:var(--r-sm);background:color-mix(in srgb,var(--danger) 7%,var(--surface));font-size:var(--fs-base);color:var(--text-1)}
.delete-account-warning b{color:var(--danger)}
.delete-account-warning ul{padding-left:20px;margin:10px 0}
.delete-account-warning p{margin:12px 0 0;color:var(--text-2);font-size:var(--fs-sm)}
.delete-account-actions{display:flex;justify-content:flex-end;flex-wrap:wrap;gap:12px;margin-top:4px}
.delete-account-actions .button{min-height:44px}
.delete-account-error{margin:0;color:var(--danger);font-size:var(--fs-base)}
</style>
