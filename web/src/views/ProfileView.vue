<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useProfileStore } from '@/stores/profile'
import { useNotice } from '@/composables/useNotice'
import type { BodyProfilePayload } from '@/api/types'
import BaseDialog from '@/components/common/BaseDialog.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import FilterSelect from '@/components/ui/FilterSelect.vue'

const props = withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false })
const emit = defineEmits<{ close: [] }>()

const auth = useAuthStore()
const profile = useProfileStore()
const notice = useNotice()
const router = useRouter()
const form = reactive<BodyProfilePayload>({ age_years: 0, biological_sex: null, height_cm: 0, weight_kg: 0 })
const biologicalSexSelection = computed<string>({
  get: () => form.biological_sex ?? '',
  set: (value) => { form.biological_sex = value === '' ? null : value as NonNullable<BodyProfilePayload['biological_sex']> },
})
const biologicalSexOptions = [
  { value: '', label: '请选择或不填写' },
  { value: 'female', label: '女性' },
  { value: 'male', label: '男性' },
  { value: 'unspecified', label: '不便提供' },
]
const weightInput = ref<number | null>(null)
const targetInput = ref<number | null>(null)
const targetDialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const deleteDialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const deleting = ref(false)
const isFirstProfile = computed(() => !profile.profile)
const recentHistory = computed(() => [...profile.weightHistory].slice(0, 8).reverse())
const targetDelta = computed(() => profile.profile?.target_weight_kg == null ? null : Math.abs(profile.profile.target_weight_kg - profile.profile.weight_kg))

watch(() => profile.profile, (value) => {
  if (value) {
    form.age_years = value.age_years
    form.biological_sex = value.biological_sex
    form.height_cm = value.height_cm
    form.weight_kg = value.weight_kg
    weightInput.value = value.weight_kg
  } else if (profile.legacyDemographics) {
    form.age_years = profile.legacyDemographics.age_years ?? 0
    form.biological_sex = profile.legacyDemographics.biological_sex
  }
}, { immediate: true })

onMounted(async () => {
  try { await profile.load() } catch (error) { notice.notify(error instanceof Error ? error.message : '身体档案暂时无法读取。', 'error') }
})

async function saveProfile(): Promise<void> {
  try {
    const result = await profile.save({
      age_years: Number(form.age_years), biological_sex: form.biological_sex || null,
      height_cm: Number(form.height_cm), weight_kg: Number(form.weight_kg),
    })
    notice.notify(result, 'success')
    if (props.embedded) emit('close')
  } catch (error) { notice.notify(error instanceof Error ? error.message : '身体档案保存失败。', 'error') }
}

async function recordWeight(): Promise<void> {
  if (weightInput.value == null) return
  try { notice.notify(await profile.recordWeight(Number(weightInput.value)), 'success') }
  catch (error) { notice.notify(error instanceof Error ? error.message : '体重记录失败。', 'error') }
}

function openTargetDialog(): void {
  targetInput.value = profile.profile?.target_weight_kg ?? null
  targetDialog.value?.open()
}

async function saveTarget(): Promise<void> {
  if (targetInput.value == null) return
  try {
    notice.notify(await profile.setTarget(Number(targetInput.value)), 'success')
    targetDialog.value?.close()
  } catch (error) { notice.notify(error instanceof Error ? error.message : '体重目标保存失败。', 'error') }
}

async function clearTarget(): Promise<void> {
  try {
    notice.notify(await profile.setTarget(null), 'success')
    targetDialog.value?.close()
  } catch (error) { notice.notify(error instanceof Error ? error.message : '体重目标清除失败。', 'error') }
}

async function removeProfile(): Promise<void> {
  deleting.value = true
  try {
    notice.notify(await profile.remove(), 'success')
    deleteDialog.value?.close()
  } catch (error) { notice.notify(error instanceof Error ? error.message : '个人身体档案和体重历史删除失败。', 'error') }
  finally { deleting.value = false }
}

function skipFirstProfile(): void {
  const userId = auth.user?.id
  if (userId) {
    try { localStorage.setItem(`fitnessCoachProfilePromptSkipped:${userId}`, 'true') } catch { /* storage may be disabled */ }
  }
  if (props.embedded) emit('close')
  else void router.push({ name: 'today' })
}
</script>

<template>
  <section class="page active profile-view" :class="{ 'is-embedded': embedded }">
    <PageHeader v-if="!embedded" title="设置与身体档案" description="管理基础档案、体重与个人目标"><template #actions><button class="button button-quiet" type="button" @click="router.push({ name: 'today' })">返回概览</button></template></PageHeader>
    <article class="panel">
      <div class="panel-head"><div><p class="eyebrow">GETTING STARTED</p><h3>{{ isFirstProfile ? '填写个人身体档案' : '编辑个人身体档案' }}</h3></div></div>
      <p class="profile-modal-intro">填写年龄、身高和当前体重；生理性别可留空。BMI 参考值会根据身高和体重计算，不需要填写体脂率或腰围。饮食规划会读取这里的年龄和性别。</p>
      <form class="form-stack" @submit.prevent="saveProfile">
        <div class="field-row"><label class="field"><span>年龄（岁）</span><input v-model.number="form.age_years" type="number" min="13" max="100" step="1" required placeholder="填写周岁" /></label>
          <label class="field"><span>生理性别（选填，用于代谢估算）</span><FilterSelect v-model="biologicalSexSelection" :options="biologicalSexOptions" aria-label="生理性别" placeholder="请选择或不填写" /></label></div>
        <div class="field-row"><label class="field"><span>身高（厘米）</span><input v-model.number="form.height_cm" type="number" min="100" max="230" step="0.1" required placeholder="例如 170" /></label>
          <label class="field"><span>当前体重（千克）</span><input v-model.number="form.weight_kg" type="number" min="25" max="300" step="0.1" required placeholder="例如 65" /></label></div>
        <div class="profile-actions"><button v-if="isFirstProfile" class="button button-quiet" type="button" @click="skipFirstProfile">跳过，稍后填写</button><button v-if="profile.profile" class="button button-danger" type="button" @click="deleteDialog?.open()">删除档案和体重记录</button><button class="button button-primary" type="submit" :disabled="profile.saving">{{ profile.saving ? '正在保存…' : '保存并继续' }}</button></div>
      </form>
    </article>
    <p class="shape-profile-link">围度、实测体脂率与骨骼肌量在塑型追踪中单独管理。<button class="text-button" type="button" @click="router.push({ name: 'shaping' })">查看塑型追踪 →</button></p>
    <div class="grid two-col profile-dashboard">
      <article class="panel"><div class="panel-head"><div><p class="eyebrow">BODY INSIGHTS</p><h3>身体数据与变化</h3></div><span class="body-insight-period">最近 12 次记录</span></div>
        <div v-if="profile.profile" class="body-insight-metrics"><article><span>BMI 参考值</span><b>{{ profile.bmi == null ? '不适用' : profile.bmi.toFixed(1) }}</b><small>{{ profile.bmi == null ? '未成年人不使用成人参考值' : '成人参考值，不作诊断' }}</small></article><article><span>当前体重</span><b>{{ profile.profile.weight_kg.toFixed(1) }}</b><small>千克</small></article><article><span>自设体重目标</span><b>{{ profile.profile.target_weight_kg == null ? '尚未设置' : `${profile.profile.target_weight_kg.toFixed(1)} kg` }}</b><small>{{ targetDelta == null ? '可单独设置体重目标' : `距离目标 ${targetDelta.toFixed(1)} kg` }}</small></article></div>
        <p v-else class="empty-state">填写身高和体重后，这里会显示 BMI 参考值和体重变化。</p>
        <div class="body-chart-dates"><span v-if="recentHistory.length">{{ recentHistory[0].date }} · {{ recentHistory[0].weight_kg }} kg</span><span v-if="recentHistory.length > 1">{{ recentHistory[recentHistory.length - 1].date }} · {{ recentHistory[recentHistory.length - 1].weight_kg }} kg</span></div>
        <div v-if="profile.profile" class="account-dialog-actions"><button class="button button-quiet" type="button" @click="openTargetDialog">{{ profile.profile.target_weight_kg == null ? '设置体重目标' : '修改体重目标' }}</button></div>
      </article>
      <article class="panel"><div class="panel-head"><div><p class="eyebrow">WEIGHT HISTORY</p><h3>体重变化</h3></div></div>
        <form v-if="profile.profile" class="quick-weight-form" @submit.prevent="recordWeight"><label class="field"><span>记录今天体重（千克）</span><input v-model.number="weightInput" type="number" min="25" max="300" step="0.1" required placeholder="例如 65" /></label><button class="button button-primary" type="submit">记录</button></form>
        <div v-if="recentHistory.length" class="weight-history-list"><ul><li v-for="entry in [...recentHistory].reverse()" :key="entry.date"><time>{{ entry.date }}</time><b>{{ entry.weight_kg }} <small>kg</small></b></li></ul></div><div v-else class="empty-state profile-empty"><p>{{ profile.profile ? '暂无体重历史。' : '保存首次身体档案后，这里会开始记录体重变化。' }}</p></div>
        <p class="fine-print">每次保存档案会记录当天体重；同一天重复保存只保留当天最新数值。</p>
      </article>
    </div>
    <article class="panel profile-privacy-card"><div><p class="eyebrow">DATA & PRIVACY</p><h3>数据与隐私</h3></div><p>训练计划和记录保存在当前账号下的本机数据库。本机演示不适合公开部署或真实健康决策。</p></article>
    <BaseDialog ref="targetDialog" class="user-dialog weight-target-dialog"><div class="user-dialog-top"><div><p class="eyebrow">WEIGHT GOAL</p><h2>设置体重目标</h2></div><button class="user-dialog-close" type="button" aria-label="关闭体重目标设置" @click="targetDialog?.close()">×</button></div><p class="weight-target-description">目标体重单独管理，只用于查看与当前体重的差距和进度，不会自动改变训练强度或推算达成时间。</p><form class="form-stack" @submit.prevent="saveTarget"><label class="field"><span>目标体重（千克）</span><input v-model.number="targetInput" type="number" min="25" max="300" step="0.1" required placeholder="例如 60" /></label><div class="account-dialog-actions weight-target-actions"><button class="button button-quiet" type="button" @click="clearTarget">清除目标</button><button class="button button-primary" type="submit">保存目标</button></div></form></BaseDialog>
    <BaseDialog ref="deleteDialog" class="user-dialog"><div class="user-dialog-top"><h2>删除个人身体档案？</h2><button class="user-dialog-close" type="button" aria-label="关闭" @click="deleteDialog?.close()">×</button></div><p>身体档案和体重历史会被删除；训练计划和训练日志会保留。</p><div class="account-dialog-actions"><button class="button button-quiet" type="button" @click="deleteDialog?.close()">取消</button><button class="button button-danger" type="button" :disabled="deleting" @click="removeProfile">确认删除</button></div></BaseDialog>
  </section>
</template>
