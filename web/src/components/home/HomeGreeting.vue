<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useDietStore } from '@/stores/diet'
import { useReviewStore } from '@/stores/review'
import { useLogStore } from '@/stores/log'
import { useProfileStore } from '@/stores/profile'
import { useShapingStore } from '@/stores/shaping'
import { localDateString } from '@/utils/date'

const auth = useAuthStore()
const diet = useDietStore()
const review = useReviewStore()
const logs = useLogStore()
const profile = useProfileStore()
const shaping = useShapingStore()
const hour = new Date().getHours()
const greeting = hour < 6 ? '夜深了' : hour < 11 ? '早上好' : hour < 14 ? '中午好' : hour < 18 ? '下午好' : '晚上好'
const nickname = computed(() => auth.user?.display_name || auth.user?.username || '训练者')
const journeyDay = computed(() => {
  const registered = review.result?.registration_date
  if (!registered) return null
  const start = new Date(`${registered}T00:00:00`)
  const current = new Date(`${localDateString()}T00:00:00`)
  return Math.max(1, Math.floor((current.getTime() - start.getTime()) / 86400000) + 1)
})
const target = computed(() => diet.targets?.target)
const streak = computed(() => {
  const dates = new Set(useHomeDates())
  let cursor = new Date()
  const dateKey = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  if (!dates.has(dateKey(cursor))) cursor.setDate(cursor.getDate() - 1)
  let count = 0
  while (dates.has(dateKey(cursor))) { count++; cursor.setDate(cursor.getDate() - 1) }
  return count
})
function useHomeDates(): string[] {
  const days = review.result?.days ?? []
  return [
    ...days.filter(day => day.logs.length || day.diet.meal_count || day.signal || day.weight_kg != null).map(day => day.date),
    ...logs.items.map(item => item.training_date), ...profile.weightHistory.map(item => item.date),
    ...shaping.measurements.map(item => item.recorded_on),
  ]
}
</script>

<template>
  <section class="home-greeting" aria-labelledby="home-title">
    <div>
      <p class="eyebrow">TODAY · {{ new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' }) }}</p>
      <h1 id="home-title">{{ greeting }}，{{ nickname }}</h1>
      <p>
        <span v-if="journeyDay">减脂塑形第 {{ journeyDay }} 天</span>
        <span v-if="target">今日基础目标 {{ target.calories_kcal }} kcal · 蛋白 {{ target.protein_g }} g</span>
        <span v-if="!journeyDay && !target">先完成今天最重要的一件事。</span>
      </p>
    </div>
    <div class="home-streak" :class="{ 'is-active': streak > 0 }"><strong>{{ streak }}</strong><span>连续记录天数</span></div>
  </section>
</template>
