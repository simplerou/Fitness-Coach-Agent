<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import HeatmapCalendar from '@/components/charts/HeatmapCalendar.vue'
import TrendChart from '@/components/charts/TrendChart.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import { useProfileStore } from '@/stores/profile'
import { useShapingStore } from '@/stores/shaping'
import { useTrainingStore } from '@/stores/training'

const profile = useProfileStore()
const shaping = useShapingStore()
const training = useTrainingStore()
const router = useRouter()
const range = ref<'4' | '8' | '12' | 'all'>('8')
const trendRows = computed(() => {
  const map = new Map<string, { weight: number | null; waist: number | null; fat: number | null }>()
  for (const item of profile.weightHistory) map.set(item.date, { weight: item.weight_kg, waist: null, fat: null })
  for (const item of shaping.measurements) {
    const row = map.get(item.recorded_on) ?? { weight: item.weight_kg, waist: null, fat: null }
    row.weight ??= item.weight_kg; row.waist = item.waist_cm; row.fat = item.body_fat_percent
    map.set(item.recorded_on, row)
  }
  const rows = [...map.entries()].sort(([a], [b]) => a.localeCompare(b))
  if (range.value === 'all') return rows
  const start = new Date(); start.setDate(start.getDate() - Number(range.value) * 7)
  return rows.filter(([date]) => new Date(`${date}T00:00:00`) >= start)
})
const heatmap = computed(() => training.logs.map((item) => ({
  date: item.training_date,
  level: item.completion === 'completed' ? 4 : item.completion === 'partial' ? 2 : 1,
  detail: `${item.planned_session_title || '训练记录'}·${item.completion === 'completed' ? '已完成' : item.completion === 'partial' ? '部分完成' : '已跳过'}${item.rpe == null ? '' : `·RPE ${item.rpe}`}`,
})))
const trendSeries = computed(() => [
  { name: '体重 kg', data: trendRows.value.map(([, row]) => row.weight), colorToken: '--brand' },
  { name: '腰围 cm', data: trendRows.value.map(([, row]) => row.waist), colorToken: '--accent' },
  { name: '体脂率 %', data: trendRows.value.map(([, row]) => row.fat), colorToken: '--warn' },
])
</script>

<template>
  <div class="overview-chart-grid">
    <SectionCard title="体重与围度趋势" subtitle="数值来自身体档案和体测记录">
      <template #actions><div class="range-switch"><button v-for="item in ['4','8','12','all'] as const" :key="item" :class="{ active: range === item }" @click="range = item">{{ item === 'all' ? '全部' : `${item}周` }}</button></div></template>
      <TrendChart :labels="trendRows.map(([date]) => date.slice(5))" :series="trendSeries" :target-line="profile.profile?.target_weight_kg" :height="270" />
    </SectionCard>
    <SectionCard title="近 3 个月训练" subtitle="颜色越深表示完成度越高">
      <HeatmapCalendar :data="heatmap" :height="270" @select="router.push({ name: 'log', query: { date: $event } })" />
    </SectionCard>
  </div>
</template>
