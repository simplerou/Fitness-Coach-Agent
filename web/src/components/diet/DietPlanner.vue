<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDietStore } from '@/stores/diet'
import { useProfileStore } from '@/stores/profile'
import { useNotice } from '@/composables/useNotice'
import TrainingTimePicker from '@/components/diet/TrainingTimePicker.vue'

const diet = useDietStore()
const bodyProfile = useProfileStore()
const notice = useNotice()
const router = useRouter()
const props = defineProps<{ consent: boolean }>()
const emit = defineEmits<{ 'update:consent': [value: boolean]; generate: [] }>()
const consentValue = computed({ get: () => props.consent, set: (value: boolean) => emit('update:consent', value) })
const profilePanel = ref<HTMLDetailsElement | null>(null)
const timePicker = ref<InstanceType<typeof TrainingTimePicker> | null>(null)
const startEndLabel = () => diet.profile.training_time && diet.profile.training_end_time
  ? `${diet.profile.training_time}–${diet.profile.training_end_time}`
  : diet.profile.training_time ? `开始 ${diet.profile.training_time}（未设置结束时间）` : '选择开始和结束时间'

async function saveProfile(): Promise<void> {
  try { notice.notify(await diet.saveProfileData(), 'success') }
  catch (error) { notice.notify(error instanceof Error ? error.message : '饮食规划档案保存失败。', 'error') }
}
function generate(): void { emit('generate') }
async function openProfile(): Promise<void> {
  if (diet.targets?.missing?.some((item) => item.includes('身体档案'))) {
    try { await bodyProfile.load() } catch { /* the profile page handles its own error */ }
    await router.push({ name: 'profile' })
    return
  }
  if (profilePanel.value) profilePanel.value.open = true
  requestAnimationFrame(() => profilePanel.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}
</script>

<template>
  <details class="panel diet-planning-fold" open>
    <summary><span><b>第一步：AI 饮食规划</b><small>先完善档案并生成初始计划；记录一段时间后，可结合实际摄入继续调整</small></span><span class="tag">先设置计划</span></summary>
    <div class="diet-planning-content">
      <details ref="profilePanel" class="panel diet-profile-panel">
        <summary><span><b>饮食规划档案</b><small>补充目标、活动水平、健康约束和饮食偏好</small></span><span class="tag">规划前填写</span></summary>
        <form class="form-stack diet-profile-form" @submit.prevent="saveProfile">
          <div class="field-row"><label class="field"><span>健身目标</span><select v-model="diet.profile.goal"><option :value="null">请选择</option><option value="fat_loss">减脂</option><option value="muscle_gain">增肌</option><option value="maintain">维持</option><option value="body_shape">塑形</option><option value="performance">提升运动表现</option></select></label><label class="field"><span>总体活动水平（包含训练）</span><select v-model="diet.profile.activity_level"><option :value="null">请选择</option><option value="sedentary">久坐为主</option><option value="light">轻度活动</option><option value="moderate">中等活动</option><option value="active">活动较多</option><option value="very_active">高活动量</option></select></label></div>
          <div class="field-row"><label class="field"><span>训练类型</span><select v-model="diet.profile.training_type"><option :value="null">请选择</option><option value="strength">力量</option><option value="cardio">有氧</option><option value="mixed">混合</option><option value="other">其他</option></select></label><label class="field"><span>通常训练时段（24小时制，选填）</span><span class="training-time-control"><button class="training-time-trigger" type="button" aria-haspopup="dialog" @click="timePicker?.open()">{{ startEndLabel() }}</button></span></label></div>
          <label class="field"><span>每日饮水参考目标（毫升，选填）</span><input v-model.number="diet.profile.water_target_ml" type="number" min="500" max="6000" step="100" placeholder="不确定可留空，只记录实际饮水" /><small class="field-hint">{{ diet.targets?.hydration?.note || '这是你自行设定的参考值，不是医疗建议；有特殊健康情况时请遵循医生建议。' }}</small><button v-if="diet.targets?.hydration?.suggested_ml" class="text-button" type="button" @click="diet.profile.water_target_ml = diet.targets?.hydration?.suggested_ml || null">使用粗略参考值</button></label>
          <p class="fine-print">年龄和性别从“我的”身体档案读取。BMR、TDEE 由系统估算；肌肉量不作为普通用户的必填数据。</p>
          <div class="field-row"><label class="field"><span>饮食偏好（如素食）</span><input v-model="diet.profile.dietary_preference" maxlength="48" placeholder="选填" /></label><label class="field"><span>过敏源</span><input v-model="diet.profile.allergies" maxlength="500" placeholder="如无过敏请留空并勾选下方确认" /></label></div>
          <label class="confirm-row"><input v-model="diet.profile.allergies_reviewed" type="checkbox" /><span>我已确认过敏源和忌口；如没有相关情况，已明确确认无。</span></label>
          <div class="field-row"><label class="field"><span>忌口食物</span><input v-model="diet.profile.avoid_foods" maxlength="500" placeholder="选填" /></label><label class="field"><span>烹饪条件</span><select v-model="diet.profile.cooking_access"><option :value="null">请选择</option><option value="none">主要外食/无厨房</option><option value="basic">简单烹饪</option><option value="full">可正常烹饪</option></select></label></div>
          <div class="field-row"><label class="field"><span>每周外食次数</span><input v-model.number="diet.profile.eating_out_per_week" type="number" min="0" max="21" placeholder="选填" /></label><label class="field"><span>预算或执行条件</span><input v-model="diet.profile.budget_note" maxlength="160" placeholder="如预算、宿舍条件等，选填" /></label></div>
          <div class="field-row"><label class="field"><span>慢性病、孕期、进食障碍或其他健康情况</span><textarea v-model="diet.profile.medical_conditions" rows="2" maxlength="500" placeholder="无则留空；填写后系统会建议咨询专业人士"></textarea></label><label class="field"><span>伤病或持续疼痛（选填）</span><textarea v-model="diet.profile.injuries" rows="2" maxlength="500" placeholder="无则留空；有情况时先咨询专业人士"></textarea></label></div>
          <label class="confirm-row"><input v-model="diet.profile.health_reviewed" type="checkbox" /><span>我已确认并填写上面的健康约束；如有特殊健康情况，愿意先咨询医生或注册营养师。</span></label>
          <label class="confirm-row diet-agent-consent"><input v-model="consentValue" type="checkbox" /><span>我同意生成 / 更新计划时，将身体指标、饮食偏好与忌口、训练安排、饮水参考值、近 7 天记录及上一版计划摘要发送给阿里云百炼（通义千问）。不会发送账号名；不勾选仍可继续使用记录功能。</span></label>
          <div class="diet-profile-actions"><button class="button button-primary" type="submit" :disabled="diet.savingProfile">保存规划档案</button><button class="button button-quiet" type="button" :disabled="diet.generatingPlan" @click="generate">{{ diet.generatingPlan ? '正在规划一周…' : '生成 / 更新本周计划' }}</button></div>
          <p class="fine-print">档案中的年龄与生理性别仅用于成人代谢公式估算。疾病、孕期、进食障碍等情况下不生成热量或营养素处方。</p>
        </form>
      </details>
      <TrainingTimePicker :start="diet.profile.training_time" :end="diet.profile.training_end_time" @update="(start, end) => { diet.profile.training_time = start; diet.profile.training_end_time = end }" />
    </div>
  </details>
</template>
