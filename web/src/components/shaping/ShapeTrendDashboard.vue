<script setup lang="ts">
import { computed, ref } from 'vue'
import TrendChart from '@/components/charts/TrendChart.vue'
import StatCard from '@/components/ui/StatCard.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import { useShapingStore } from '@/stores/shaping'

const shaping = useShapingStore()
const range = ref<'4' | '8' | '12' | 'all'>('8')
const rows = computed(() => {
  const map = new Map<string, { weight: number | null; waist: number | null; fat: number | null; muscle: number | null }>()
  for (const item of shaping.data?.weight_history ?? []) map.set(item.date, { weight: item.weight_kg, waist: null, fat: null, muscle: null })
  for (const item of shaping.measurements) {
    const row = map.get(item.recorded_on) ?? { weight: item.weight_kg, waist: null, fat: null, muscle: null }
    row.weight ??= item.weight_kg; row.waist = item.waist_cm; row.fat = item.body_fat_percent; row.muscle = item.skeletal_muscle_kg
    map.set(item.recorded_on, row)
  }
  const values = [...map.entries()].sort(([a], [b]) => a.localeCompare(b))
  if (range.value === 'all') return values
  const start = new Date(); start.setDate(start.getDate() - Number(range.value) * 7)
  return values.filter(([date]) => new Date(`${date}T00:00:00`) >= start)
})
const series = computed(() => [
  { name: '体重 kg', data: rows.value.map(([, item]) => item.weight), colorToken: '--brand' },
  { name: '腰围 cm', data: rows.value.map(([, item]) => item.waist), colorToken: '--accent' },
  { name: '体脂率 %', data: rows.value.map(([, item]) => item.fat), colorToken: '--warn' },
  { name: '骨骼肌 kg', data: rows.value.map(([, item]) => item.muscle), colorToken: '--success' },
])
function metric(key: 'weight' | 'waist' | 'fat') {
  const values = rows.value.map(([, item]) => item[key]).filter((value): value is number => value != null)
  return { current: values.at(-1) ?? null, delta: values.length > 1 ? values.at(-1)! - values.at(-2)! : null }
}
</script>

<template>
  <SectionCard title="身体趋势" subtitle="同一日的多项指标会在悬停时对齐显示">
    <template #actions><div class="range-switch"><button v-for="item in ['4','8','12','all'] as const" :key="item" :class="{ active: range === item }" @click="range = item">{{ item === 'all' ? '全部' : `${item}周` }}</button></div></template>
    <TrendChart :labels="rows.map(([date]) => date)" :series="series" :height="380" />
  </SectionCard>
  <div class="report-stat-grid">
    <StatCard label="当前体重" :value="metric('weight').current ?? '未记录'" :unit="metric('weight').current == null ? '' : 'kg'" :trend="metric('weight').delta == null ? undefined : { delta: `${Math.abs(metric('weight').delta!).toFixed(1)} kg`, direction: metric('weight').delta! > 0 ? 'up' : metric('weight').delta! < 0 ? 'down' : 'flat' }" sub="与上次记录对比" />
    <StatCard label="当前腰围" :value="metric('waist').current ?? '未记录'" :unit="metric('waist').current == null ? '' : 'cm'" :trend="metric('waist').delta == null ? undefined : { delta: `${Math.abs(metric('waist').delta!).toFixed(1)} cm`, direction: metric('waist').delta! > 0 ? 'up' : metric('waist').delta! < 0 ? 'down' : 'flat' }" sub="围度建议每两周同条件测量" />
    <StatCard label="当前体脂率" :value="metric('fat').current ?? '未记录'" :unit="metric('fat').current == null ? '' : '%'" :trend="metric('fat').delta == null ? undefined : { delta: `${Math.abs(metric('fat').delta!).toFixed(1)} 个百分点`, direction: metric('fat').delta! > 0 ? 'up' : metric('fat').delta! < 0 ? 'down' : 'flat' }" sub="仅对比实测读数" />
  </div>
</template>
