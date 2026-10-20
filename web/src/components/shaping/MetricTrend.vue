<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ label: string; unit: string; entries: { date: string; value: number }[] }>()
const recent = computed(() => props.entries.slice(-12))
const points = computed(() => {
  const entries = recent.value
  const values = entries.map(row => row.value)
  const min = Math.min(...values) - 1
  const range = Math.max(...values) - min + 1
  const first = Date.parse(entries[0]?.date ?? '')
  const last = Date.parse(entries.at(-1)?.date ?? '')
  return entries.map(entry => ({
    x: entries.length === 1 ? 260 : 30 + (Date.parse(entry.date) - first) / Math.max(1, last - first) * 460,
    y: 105 - (entry.value - min) / range * 80, ...entry,
  }))
})
</script>

<template>
  <div class="shape-trend">
    <p v-if="!recent.length" class="shape-muted">还没有{{ label }}记录，填写后会显示变化。</p>
    <template v-else>
      <svg viewBox="0 0 520 135" role="img" :aria-label="`${label}最近${recent.length}次记录，单位${unit}`">
        <line x1="25" y1="111" x2="495" y2="111" stroke="var(--line)" />
        <polyline v-if="points.length > 1" :points="points.map(p => `${p.x},${p.y}`).join(' ')" fill="none" stroke="var(--green)" stroke-width="2" />
        <g v-for="point in points" :key="point.date"><circle :cx="point.x" :cy="point.y" r="4" fill="var(--green)"><title>{{ point.date }}：{{ point.value }} {{ unit }}</title></circle><text :x="point.x" :y="point.y - 10" text-anchor="middle" fill="var(--ink)" font-size="11">{{ point.value }}</text></g>
      </svg>
      <div class="shape-trend-dates"><span>{{ recent[0].date }}</span><span>{{ recent.at(-1)?.date }}</span></div>
      <p class="fine-print">{{ recent.length === 1 ? '已有首次记录，再测量一次就能比较变化。' : '按实际日期展示最近 12 次读数；连线用于查看趋势，不代表缺失日期的读数。' }}</p>
      <details class="shape-trend-values"><summary>查看具体读数</summary><ul><li v-for="entry in recent" :key="entry.date">{{ entry.date }} · {{ entry.value }} {{ unit }}</li></ul></details>
    </template>
  </div>
</template>
