<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'
import { useProfileStore } from '@/stores/profile'
import { useShapingStore } from '@/stores/shaping'

const TrendChart = defineAsyncComponent(() => import('./ProgressTrendChart.vue'))
const profile = useProfileStore()
const shaping = useShapingStore()
const router = useRouter()
const latest = computed(() => shaping.measurements.at(-1) ?? null)
const goal = computed(() => {
  const current = profile.profile?.weight_kg
  const target = profile.profile?.target_weight_kg
  const start = profile.weightHistory[0]?.weight_kg
  if (current == null || target == null) return null
  const gap = Math.abs(current - target)
  const total = start == null ? null : Math.abs(start - target)
  const progress = total && total > 0 ? Math.max(0, Math.min(100, (1 - gap / total) * 100)) : null
  return { gap, progress }
})
const metrics = computed(() => [
  { label: '体重', value: profile.profile?.weight_kg, unit: 'kg', action: '记录体重' },
  { label: '腰围', value: latest.value?.waist_cm, unit: 'cm', action: '去测量' },
  { label: '体脂率', value: latest.value?.body_fat_percent, unit: '%', action: '去记录' },
  { label: '骨骼肌', value: latest.value?.skeletal_muscle_kg, unit: 'kg', action: '去记录' },
])
</script>

<template>
  <div class="home-progress-main">
    <TrendChart :weights="profile.weightHistory" :measurements="shaping.measurements" />
    <div class="home-goal-progress">
      <template v-if="goal"><div><span>体重目标进度</span><strong>距目标还差 {{ goal.gap.toFixed(1) }} kg</strong></div><progress v-if="goal.progress != null" :value="goal.progress" max="100">{{ goal.progress.toFixed(0) }}%</progress></template>
      <template v-else><span>还没有体重目标</span><button class="text-button" @click="router.push({ name: 'profile' })">设置目标 →</button></template>
    </div>
  </div>
  <div class="home-metric-row">
    <article v-for="item in metrics" :key="item.label">
      <span>{{ item.label }}</span>
      <strong v-if="item.value != null">{{ Number(item.value).toFixed(1) }} <small>{{ item.unit }}</small></strong>
      <button v-else class="text-button" @click="router.push({ name: item.label === '体重' ? 'profile' : 'shaping' })">{{ item.action }} →</button>
    </article>
  </div>
  <button class="home-photo-link" @click="router.push({ name: 'shaping', query: { section: 'photos' } })"><span>三视角对比照</span><strong>{{ shaping.photos.length ? `已有 ${shaping.photos.length} 张，查看变化` : '添加第一张对比照' }} →</strong></button>
</template>
