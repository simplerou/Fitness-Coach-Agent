<script setup lang="ts">
import { computed, ref } from 'vue'
import { useShapingStore } from '@/stores/shaping'
import { CIRCUMFERENCES, SHAPE_LABELS } from '@/constants/shaping'
import { signedDifference } from '@/utils/shaping'
import type { ShapeCircumference } from '@/api/types'
import MetricTrend from './MetricTrend.vue'
import MeasurementGuide from './MeasurementGuide.vue'
defineEmits<{ record: [] }>()
const shaping = useShapingStore()
const selected = ref<ShapeCircumference>('waist_cm')
const entries = computed(() => shaping.measurements.filter(row => row[selected.value] != null).map(row => ({ date: row.recorded_on, value: row[selected.value]! })))
function change(metric: ShapeCircumference): string {
  const rows = shaping.measurements.filter(row => row[metric] != null)
  return signedDifference(rows.at(-1)?.[metric] ?? null, rows.at(-2)?.[metric] ?? null, 'cm')
}
</script>

<template>
  <article class="panel shape-panel">
    <div class="panel-head"><div><p class="eyebrow">MEASURE, THEN COMPARE</p><h3>围度追踪</h3></div><button class="text-button" @click="$emit('record')">补充测量</button></div>
    <div class="shape-circumferences"><button v-for="metric in CIRCUMFERENCES" :key="metric" class="shape-metric-card" :class="{ selected: selected === metric }" :aria-pressed="selected === metric" @click="selected = metric"><span>{{ SHAPE_LABELS[metric] }}</span><strong>{{ shaping.latest(metric)?.[metric]?.toFixed(1) ?? '未记录' }} <small v-if="shaping.latest(metric)">cm</small></strong><span>{{ change(metric) }}</span><small>{{ shaping.latest(metric)?.recorded_on ?? '等待首次测量' }}</small></button></div>
    <MetricTrend :label="SHAPE_LABELS[selected]" unit="cm" :entries="entries" />
    <MeasurementGuide />
  </article>
</template>
