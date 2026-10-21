<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { usePlanStore } from '@/stores/plan'
import type { PlanPreferences } from '@/api/types'
import type { ExerciseDefinition } from '@/api/types'
import { useTrainingStore } from '@/stores/training'
import ExerciseLibrary from '@/components/training/ExerciseLibrary.vue'
import FilterSelect from '@/components/ui/FilterSelect.vue'

const plan = usePlanStore()
const router = useRouter()
const training = useTrainingStore()
const showExercises = ref(false)
const selectedExercises = computed(() => training.exercises.filter((item) => plan.preferences.preferred_exercise_ids.includes(item.id)))
onMounted(() => { if (!training.exercises.length) void training.loadExercises() })
const goalOptions = [
  { value: 'fitness', title: '综合体能', summary: '力量练习与轻松有氧交替安排。' },
  { value: 'strength', title: '力量基础', summary: '以熟悉、安全的力量练习作为主要方向。' },
  { value: 'fat_loss', title: '提升日常活动', summary: '从可持续的日常活动和基础力量开始。' },
] as const
const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const equipmentOptions: Array<{ value: PlanPreferences['equipment'][number]; label: string }> = [
  { value: 'bodyweight_only', label: '仅自重' }, { value: 'dumbbells', label: '哑铃' },
  { value: 'resistance_bands', label: '弹力带' }, { value: 'gym', label: '健身房常见器械' },
]
const rec = computed(() => plan.recommendation())
const experienceOptions = [{ value: 'beginner', label: '刚开始训练' }, { value: 'some_experience', label: '有一些经验' }, { value: 'experienced', label: '经验较丰富' }]
const sessionDurationOptions = [20, 30, 45, 60].map(value => ({ value: String(value), label: `约 ${value} 分钟` }))
function setExperience(value: string): void { plan.preferences.experience_level = value as PlanPreferences['experience_level']; plan.edited = true }
function setSessionDuration(value: string): void { plan.preferences.session_minutes = Number(value) as PlanPreferences['session_minutes']; plan.edited = true }

function toggleWeekday(day: number): void {
  plan.edited = true
  const next = new Set(plan.preferences.training_weekdays)
  if (next.has(day)) next.delete(day)
  else if (next.size < 6) next.add(day)
  else return
  plan.preferences.training_weekdays = [...next].sort((a, b) => a - b)
  plan.preferences.days_per_week = next.size
}

function toggleEquipment(value: PlanPreferences['equipment'][number]): void {
  plan.edited = true
  if (value === 'bodyweight_only') {
    plan.preferences.equipment = plan.preferences.equipment.includes(value) ? [] : [value]
    removeIncompatiblePreferredExercises()
    return
  }
  plan.preferences.equipment = plan.preferences.equipment.filter((item) => item !== 'bodyweight_only')
  plan.preferences.equipment = plan.preferences.equipment.includes(value)
    ? plan.preferences.equipment.filter((item) => item !== value)
    : [...plan.preferences.equipment, value]
  removeIncompatiblePreferredExercises()
}

function removeIncompatiblePreferredExercises(): void {
  if (!training.exercises.length) return
  const selectedEquipment = plan.preferences.equipment
  plan.preferences.preferred_exercise_ids = plan.preferences.preferred_exercise_ids.filter((id) => {
    const exercise = training.exercises.find((item) => item.id === id)
    return Boolean(exercise && exercise.equipment.some((item) => selectedEquipment.includes(item as PlanPreferences['equipment'][number])))
  })
}

function changeGoal(value: PlanPreferences['goal']): void {
  plan.preferences.goal = value
  plan.edited = true
}
function addExercise(item: ExerciseDefinition): void {
  if (plan.preferences.preferred_exercise_ids.includes(item.id)) return
  if (plan.preferences.preferred_exercise_ids.length >= 12) return
  plan.preferences.preferred_exercise_ids.push(item.id); plan.edited = true
}
function removeExercise(id: number): void {
  plan.preferences.preferred_exercise_ids = plan.preferences.preferred_exercise_ids.filter((item) => item !== id)
  plan.edited = true
}
</script>

<template>
  <section class="panel plan-direction-module" aria-labelledby="plan-direction-title">
    <div class="panel-head"><div><p class="eyebrow">YOUR STARTING POINT</p><h3 id="plan-direction-title">根据身体档案，选择训练方向</h3></div><span class="step-no">00</span></div>
    <p class="plan-recommendation-context">{{ rec.context || rec.reason }}</p>
    <div class="plan-goal-options" role="group" aria-label="选择训练方向">
      <button v-for="option in goalOptions" :key="option.value" class="plan-goal-card" :class="{ selected: plan.preferences.goal === option.value }" type="button" :aria-pressed="plan.preferences.goal === option.value" @click="changeGoal(option.value)">
        <span class="plan-goal-card-top"><b>{{ option.title }}</b><i v-if="rec.goal === option.value">推荐起点</i></span>
        <span class="plan-goal-card-summary">{{ option.summary }}</span><span class="goal-selected-label">{{ plan.preferences.goal === option.value ? '已选择' : '选择方向' }}</span>
      </button>
    </div>
    <p class="fine-print">推荐方向只是计划起点。选定后，下面的训练日、经验、器械和时长仍由你决定。</p>
    <button v-if="!plan.recommendation().context" class="text-button" type="button" @click="router.push({ name: 'profile' })">先填写身体档案</button>
  </section>

  <article class="panel">
    <div class="panel-head"><div><p class="eyebrow">YOUR PREFERENCES</p><h3>告诉我你的安排</h3></div><span class="step-no">01</span></div>
    <form class="form-stack" @submit.prevent="$emit('generate')">
      <fieldset class="weekday-fieldset"><legend>每周训练星期（选择 1–6 天）</legend>
        <div class="weekday-grid"><label v-for="(day, index) in weekdays" :key="day" class="weekday-option"><input type="checkbox" :checked="plan.preferences.training_weekdays.includes(index + 1)" @change="toggleWeekday(index + 1)" /><span>{{ day }}</span></label></div>
        <p class="weekday-count" aria-live="polite">已选 {{ plan.preferences.training_weekdays.length }} 天</p>
      </fieldset>
      <label class="field"><span>训练经验</span><FilterSelect :model-value="plan.preferences.experience_level" :options="experienceOptions" aria-label="训练经验" @update:model-value="setExperience" /></label>
      <fieldset class="form-stack equipment-options"><legend>可用器械（至少选择一项）</legend>
        <label v-for="item in equipmentOptions" :key="item.value" class="check-row"><input type="checkbox" :checked="plan.preferences.equipment.includes(item.value)" @change="toggleEquipment(item.value)" /><span>{{ item.label }}</span></label>
        <p class="fine-print">“仅自重”与其他器械选项互斥；可同时选择多种器械。</p>
      </fieldset>
      <fieldset class="exercise-preference-field"><legend>偏好动作（可选，最多 12 个）</legend><p class="fine-print">仅显示与上方器械匹配的动作。不选择时会按可用器械自动搭配常见动作；选择后力量训练日优先沿用这些动作。点击查看动作要领。</p><div v-if="selectedExercises.length" class="selected-exercise-chips"><button v-for="item in selectedExercises" :key="item.id" type="button" @click="removeExercise(item.id)">{{ item.name }} ×</button></div><button class="button button-quiet" type="button" @click="showExercises = !showExercises">{{ showExercises ? '收起动作库' : '从动作库选择' }}</button><ExerciseLibrary v-if="showExercises" compact selectable :equipment-filter="plan.preferences.equipment" @select="addExercise" /></fieldset>
      <label class="field"><span>单次训练时长</span><FilterSelect :model-value="String(plan.preferences.session_minutes)" :options="sessionDurationOptions" aria-label="单次训练时长" @update:model-value="setSessionDuration" /></label>
      <button class="button button-primary" type="submit" :disabled="plan.generating">{{ plan.generating ? '正在生成…' : '生成本周计划 ↗' }}</button>
    </form>
    <p class="fine-print">生成计划时会将本次训练偏好、用于安全提示的年龄段和候选动作发送给项目配置的通义千问模型；不会发送账号标识或具体身高体重数值。</p>
    <p class="fine-print">生成计划前需填写个人身体档案。年龄会影响恢复提示；身高体重用于后续进展对照。</p>
  </article>
</template>

<script lang="ts">export default { emits: ['generate'] }</script>
