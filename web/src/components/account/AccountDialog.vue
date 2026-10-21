<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getPlanPreferences } from '@/api/plan'
import { useAuthStore } from '@/stores/auth'
import { useProfileStore } from '@/stores/profile'
import { useNotice } from '@/composables/useNotice'
import AvatarCropDialog from '@/components/account/AvatarCropDialog.vue'
import BaseDialog from '@/components/common/BaseDialog.vue'
import type { PlanPreferences } from '@/api/types'

const emit = defineEmits<{ avatarSaved: [dataUrl: string]; close: [] }>()
const auth = useAuthStore()
const profile = useProfileStore()
const notice = useNotice()
const router = useRouter()
const dialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const avatarCrop = ref<InstanceType<typeof AvatarCropDialog> | null>(null)
const avatar = ref('')
const goal = ref<PlanPreferences['goal'] | null>(null)
const weightInput = ref<number | null>(null)
const targetInput = ref<number | null>(null)
const targetDialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const saving = ref(false)
const delta = computed(() => {
  const history = [...profile.weightHistory].slice(0, 12).reverse()
  return history.length < 2 ? null : history[history.length - 1].weight_kg - history[history.length - 2].weight_kg
})
const goalLabel = computed(() => ({ fitness: '综合体能', strength: '力量基础', fat_loss: '增加日常活动' }[goal.value || 'fitness']))

async function open(): Promise<void> {
  dialog.value?.open()
  avatar.value = auth.user ? localStorage.getItem(`fitnessCoachAvatar:${auth.user.id}`) || '' : ''
  try { await profile.load(); weightInput.value = profile.profile?.weight_kg ?? null }
  catch (error) { notice.notify(error instanceof Error ? error.message : '身体档案暂时无法读取。', 'error') }
  try { goal.value = (await getPlanPreferences()).preferences.goal }
  catch { goal.value = null }
}
function close(): void { dialog.value?.close() }
async function logout(): Promise<void> {
  try { await auth.logout(); close() }
  catch (error) { notice.notify(error instanceof Error ? error.message : '退出登录失败。', 'error') }
}
async function recordWeight(): Promise<void> {
  if (weightInput.value == null) return
  saving.value = true
  try { notice.notify(await profile.recordWeight(weightInput.value), 'success') }
  catch (error) { notice.notify(error instanceof Error ? error.message : '体重记录失败。', 'error') }
  finally { saving.value = false }
}
function openTarget(): void {
  if (!profile.profile) { notice.notify('请先管理身体档案，再设置体重目标。', 'error'); return }
  targetInput.value = profile.profile.target_weight_kg
  targetDialog.value?.open()
}
async function saveTarget(value: number | null): Promise<void> {
  try {
    notice.notify(await profile.setTarget(value), 'success')
    targetDialog.value?.close()
  } catch (error) { notice.notify(error instanceof Error ? error.message : '体重目标保存失败。', 'error') }
}
function avatarUpdated(dataUrl: string): void { avatar.value = dataUrl; emit('avatarSaved', dataUrl) }

defineExpose({ open })
</script>

<template>
  <BaseDialog ref="dialog" class="user-dialog" aria-labelledby="account-title" @close="$emit('close')">
    <div class="user-dialog-top"><p class="eyebrow">用户数据</p><button class="user-dialog-close" type="button" aria-label="关闭用户信息" @click="close">×</button></div>
    <div class="account-dialog-identity">
      <div class="account-avatar-wrap"><button class="account-avatar-button" type="button" aria-label="更换头像" @click="avatarCrop?.openPicker()"><span class="user-avatar" :class="{ 'has-avatar-image': avatar }"><img v-if="avatar" :src="avatar" alt="" /><template v-else>禾</template></span></button></div>
      <div><p class="eyebrow">本机账号</p><h2 id="account-title">{{ auth.user?.display_name }}</h2><p>账号：{{ auth.user?.username }}</p></div>
    </div>
    <section class="account-dialog-profile"><h3>身体档案</h3>
      <div v-if="profile.profile" class="account-profile-grid"><div><span>年龄</span><strong>{{ profile.profile.age_years }} 岁</strong></div><div><span>性别</span><strong>{{ { female: '女性', male: '男性', unspecified: '不便提供' }[profile.profile.biological_sex || 'unspecified'] }}</strong></div><div><span>身高</span><strong>{{ profile.profile.height_cm }} 厘米</strong></div><div><span>当前体重</span><strong>{{ profile.profile.weight_kg }} 千克</strong></div></div>
      <p v-else>{{ profile.loading ? '正在读取身体档案…' : '尚未填写身体档案' }}</p>
    </section>
    <section v-if="profile.profile" class="body-insight-module">
      <div class="body-insight-heading"><div><p class="eyebrow">BODY INSIGHTS</p><h3>身体数据与变化</h3></div><span class="body-insight-period">最近 12 次记录</span></div>
      <div class="body-insight-metrics"><article><span>BMI 参考值</span><b>{{ profile.bmi == null ? '不适用' : profile.bmi.toFixed(1) }}</b><small>{{ profile.bmi == null ? '未成年人不使用成人参考值' : '成人参考值，不作诊断' }}</small></article><article><span>当前体重</span><b>{{ profile.profile.weight_kg.toFixed(1) }}</b><small>千克</small></article><article><span>较上次记录</span><b>{{ delta == null ? '暂无' : `${delta > 0 ? '+' : ''}${delta.toFixed(1)}` }}</b><small>千克</small></article></div>
      <div class="body-chart-dates"><span v-for="entry in profile.weightHistory.slice(0, 12).reverse()" :key="entry.date">{{ entry.date }} · {{ entry.weight_kg }} kg</span></div>
      <div class="body-weight-target"><div><span>自设体重目标</span><b>{{ profile.profile.target_weight_kg == null ? '尚未设置' : `${profile.profile.target_weight_kg.toFixed(1)} kg` }}</b><small>{{ profile.profile.target_weight_kg == null ? '可单独设置体重目标' : `距离目标 ${Math.abs(profile.profile.target_weight_kg - profile.profile.weight_kg).toFixed(1)} kg` }}</small></div><button class="text-button" type="button" @click="openTarget">{{ profile.profile.target_weight_kg == null ? '设置体重目标' : '修改体重目标' }}</button></div>
      <form class="quick-weight-form" @submit.prevent="recordWeight"><label class="field"><span>记录今天体重（千克）</span><input v-model.number="weightInput" type="number" min="25" max="300" step="0.1" required placeholder="例如 65" /></label><button class="button button-primary" type="submit" :disabled="saving">记录</button></form>
      <div class="body-goal-link"><div><span>当前训练目标</span><b>{{ goalLabel }}</b></div><button class="text-button" type="button" @click="close(); router.push({ name: 'plan' })">调整目标</button></div>
      <p class="body-insight-note">BMI 仅作成年人群的参考，不用于诊断；体重趋势用于回顾，不会单独改变训练强度。</p>
    </section>
    <div class="account-dialog-note">训练计划和记录保存在当前账号下的本机数据库。</div>
    <div class="body-goal-link"><div><span>围度 · 体成分 · 对比照</span><b>塑型追踪</b></div><button class="text-button" type="button" @click="close(); router.push({ name: 'shaping' })">查看变化</button></div>
    <BaseDialog ref="targetDialog" class="user-dialog weight-target-dialog" aria-labelledby="target-title"><div class="user-dialog-top"><div><p class="eyebrow">WEIGHT GOAL</p><h2 id="target-title">设置体重目标</h2></div><button class="user-dialog-close" type="button" aria-label="关闭体重目标设置" @click="targetDialog?.close()">×</button></div><p class="weight-target-description">目标体重单独管理，只用于查看与当前体重的差距和进度，不会自动改变训练强度或推算达成时间。</p><form class="form-stack" @submit.prevent="saveTarget(targetInput)"><label class="field"><span>目标体重（千克）</span><input v-model.number="targetInput" type="number" min="25" max="300" step="0.1" required placeholder="例如 60" /></label><div class="account-dialog-actions weight-target-actions"><button class="button button-quiet" type="button" @click="saveTarget(null)">清除目标</button><button class="button button-primary" type="submit">保存目标</button></div></form></BaseDialog>
    <AvatarCropDialog ref="avatarCrop" @saved="avatarUpdated" />
  </BaseDialog>
</template>
