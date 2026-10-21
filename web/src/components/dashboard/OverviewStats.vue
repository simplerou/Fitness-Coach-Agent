<script setup lang="ts">
import { computed } from 'vue'
import RingProgress from '@/components/charts/RingProgress.vue'
import StatCard from '@/components/ui/StatCard.vue'
import { useDietStore } from '@/stores/diet'
import { useHomeStore } from '@/stores/home'
import { useLogStore } from '@/stores/log'
import { useProfileStore } from '@/stores/profile'
import { useSafetyStore } from '@/stores/safety'
import { localDateString, shiftDate } from '@/utils/date'

const diet = useDietStore()
const home = useHomeStore()
const logs = useLogStore()
const profile = useProfileStore()
const safety = useSafetyStore()
const target = computed(() => diet.targets?.target ?? null)
const calories = computed(() => Math.round(diet.sums.calories_kcal.value))
const macros = computed(() => [
  { label: '蛋白质', value: diet.sums.protein_g.value, target: target.value?.protein_g ?? 0 },
  { label: '碳水', value: diet.sums.carbs_g.value, target: target.value?.carbs_g ?? 0 },
  { label: '脂肪', value: diet.sums.fat_g.value, target: target.value?.fat_g ?? 0 },
])
const level = computed(() => safety.today?.level ?? 'insufficient_data')
const levelLabel = computed(() => safety.levelLabel(level.value)[0])
const completed = computed(() => home.todayLog?.completion === 'completed')
const plannedExercises = computed(() => {
  const exercises = safety.today?.today_schedule?.session?.exercises
  return Array.isArray(exercises) ? exercises.length : 0
})
const streak = computed(() => {
  const set = new Set(logs.items.filter((item) => item.completion !== 'skipped').map((item) => item.training_date))
  let days = 0
  let cursor = localDateString()
  while (set.has(cursor)) { days += 1; cursor = shiftDate(cursor, -1) }
  return days
})
const weekDots = computed(() => Array.from({ length: 7 }, (_, index) => {
  const date = shiftDate(localDateString(), index - 6)
  return logs.items.some((item) => item.training_date === date && item.completion !== 'skipped')
}))
const currentWeight = computed(() => profile.profile?.weight_kg ?? null)
const targetWeight = computed(() => profile.profile?.target_weight_kg ?? null)
const baseline = computed(() => profile.weightHistory[0]?.weight_kg ?? currentWeight.value)
const weightProgress = computed(() => {
  if (currentWeight.value == null || targetWeight.value == null || baseline.value == null) return 0
  const total = Math.abs(baseline.value - targetWeight.value)
  return total ? Math.min(100, Math.max(0, Math.abs(baseline.value - currentWeight.value) / total * 100)) : 100
})
</script>

<template>
  <div class="overview-stat-grid">
    <article class="stat-card data-card calorie-card">
      <div class="stat-card-head"><span>今日热量</span><span>{{ target ? '摄入 / 目标' : '待设置目标' }}</span></div>
      <div class="calorie-card-main">
        <RingProgress :value="calories" :max="target?.calories_kcal ?? 0" :tone="target && calories > target.calories_kcal ? 'danger' : 'brand'" unit="kcal" label="已摄入" :size="108" />
        <div class="macro-mini-list">
          <div v-for="item in macros" :key="item.label"><span>{{ item.label }}</span><b>{{ Math.round(item.value) }} / {{ item.target || '未设置' }}<small v-if="item.target"> g</small></b><i><span :style="{ width: `${item.target ? Math.min(100, item.value / item.target * 100) : 0}%` }" /></i></div>
        </div>
      </div>
    </article>
    <StatCard label="今日训练" :value="completed ? '已完成' : safety.today?.today_schedule?.status === 'rest' ? '休息日' : '待行动'" :sub="plannedExercises ? `计划 ${plannedExercises} 个动作` : safety.today?.today_schedule?.message || '未安排训练'" :tone="level === 'stop' ? 'danger' : level === 'downgrade' ? 'warn' : level === 'rest_day' ? 'default' : 'success'">
      <span class="status-pill" :class="`level-${level}`">{{ levelLabel }}</span>
    </StatCard>
    <StatCard label="连续打卡" :value="streak" unit="天" :sub="`最近 7 天完成 ${weekDots.filter(Boolean).length} 天`" tone="brand">
      <div class="week-dot-row" aria-label="最近七天打卡"><i v-for="(done, index) in weekDots" :key="index" :class="{ done }" /></div>
    </StatCard>
    <StatCard label="体重目标" :value="currentWeight ?? '未记录'" :unit="currentWeight == null ? '' : 'kg'" :sub="targetWeight == null ? '设置目标后查看进度' : `目标 ${targetWeight} kg · 剩余 ${Math.abs((currentWeight ?? targetWeight) - targetWeight).toFixed(1)} kg`" tone="brand">
      <div class="target-progress"><i><span :style="{ width: `${weightProgress}%` }" /></i><b>{{ Math.round(weightProgress) }}%</b></div>
    </StatCard>
  </div>
</template>
