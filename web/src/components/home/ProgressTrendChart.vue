<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ShapeMeasurement, WeightHistoryItem } from '@/api/types'

const props = defineProps<{ weights: WeightHistoryItem[]; measurements: ShapeMeasurement[] }>()
type Metric = 'weight' | 'waist'
const metric = ref<Metric>(props.weights.length ? 'weight' : 'waist')
const hoverIndex = ref<number | null>(null)
const rows = computed(() => metric.value === 'weight'
  ? props.weights.slice(-12).map(row => ({ date: row.date, value: row.weight_kg }))
  : props.measurements.filter(row => row.waist_cm != null).slice(-12).map(row => ({ date: row.recorded_on, value: Number(row.waist_cm) })))
const unit = computed(() => metric.value === 'weight' ? 'kg' : 'cm')
const label = computed(() => metric.value === 'weight' ? '体重' : '腰围')
const points = computed(() => {
  if (!rows.value.length) return []
  const values = rows.value.map(row => row.value)
  const min = Math.min(...values); const max = Math.max(...values); const span = Math.max(max - min, 1)
  return rows.value.map((row, index) => ({ ...row, x: rows.value.length === 1 ? 50 : 4 + index * 92 / (rows.value.length - 1), y: 84 - (row.value - min) / span * 68 }))
})
const path = computed(() => points.value.map(point => `${point.x},${point.y}`).join(' '))
</script>

<template>
  <div class="home-chart">
    <div class="home-chart-tabs" aria-label="趋势指标">
      <button :aria-pressed="metric === 'weight'" :disabled="!weights.length" @click="metric = 'weight'">体重</button>
      <button :aria-pressed="metric === 'waist'" :disabled="!measurements.some(row => row.waist_cm != null)" @click="metric = 'waist'">腰围</button>
    </div>
    <div v-if="points.length" class="home-chart-canvas">
      <svg viewBox="0 0 100 92" preserveAspectRatio="none" role="img" :aria-label="`近 ${points.length} 次${label}趋势`" @mouseleave="hoverIndex = null">
        <defs><linearGradient id="home-chart-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#70a982" stop-opacity=".3"/><stop offset="1" stop-color="#70a982" stop-opacity="0"/></linearGradient></defs>
        <line x1="4" y1="84" x2="96" y2="84" />
        <polygon :points="`4,84 ${path} 96,84`" fill="url(#home-chart-fill)" />
        <polyline :points="path" />
        <circle v-for="(point, index) in points" :key="point.date" :cx="point.x" :cy="point.y" r="1.7" tabindex="0" @mouseenter="hoverIndex = index" @focus="hoverIndex = index" />
      </svg>
      <div v-if="hoverIndex != null && points[hoverIndex]" class="home-chart-tooltip" role="status">
        {{ points[hoverIndex].date }} · {{ points[hoverIndex].value.toFixed(1) }} {{ unit }}
      </div>
      <div class="home-chart-range"><span>{{ points[0]?.date }}</span><span>{{ points.at(-1)?.date }}</span></div>
      <details><summary>查看趋势数据</summary><ul><li v-for="row in rows" :key="row.date">{{ row.date }}：{{ row.value.toFixed(1) }} {{ unit }}</li></ul></details>
    </div>
    <div v-else class="home-empty-inline"><p>还没有{{ label }}趋势数据。</p></div>
  </div>
</template>
