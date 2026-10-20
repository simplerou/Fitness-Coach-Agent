<script setup lang="ts">
import { ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import AccountDialog from '@/components/account/AccountDialog.vue'

const auth = useAuthStore()
const account = ref<InstanceType<typeof AccountDialog> | null>(null)
const avatar = ref('')
watch(() => auth.user?.id, (id) => {
  try { avatar.value = id ? localStorage.getItem(`fitnessCoachAvatar:${id}`) || '' : '' }
  catch { avatar.value = '' }
}, { immediate: true })
function openAccount(): void { account.value?.open() }
</script>

<template>
  <header class="topbar">
    <a class="brand" href="#/today" aria-label="青禾训练助理首页">
      <span class="brand-mark">禾</span>
      <span><strong>青禾</strong><small>训练助理 · V1.9</small></span>
    </a>
    <div class="account-actions">
      <button v-if="auth.isAuthenticated" class="user-menu-button" type="button" aria-label="打开用户信息" aria-haspopup="dialog" aria-controls="account-dialog" @click="openAccount">
        <span class="user-menu-avatar" :class="{ 'has-avatar-image': avatar }" aria-hidden="true"><img v-if="avatar" :src="avatar" alt="" /><template v-else>禾</template></span>
      </button>
      <span class="local-badge"><i></i> 本机账号演示</span>
    </div>
    <AccountDialog ref="account" @avatar-saved="avatar = $event" />
  </header>
</template>
