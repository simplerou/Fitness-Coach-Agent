<script setup lang="ts">
import { computed, ref } from 'vue'
import { useShapingStore } from '@/stores/shaping'
import { SOURCE_LABELS } from '@/constants/shaping'
import { signedDifference } from '@/utils/shaping'
import MetricTrend from './MetricTrend.vue'
defineEmits<{ record: []; weight: [] }>()
const shaping = useShapingStore()
const selected = ref<'body_fat_percent' | 'skeletal_muscle_kg'>('body_fat_percent')
const entries = computed(() => shaping.measurements.filter(row => row[selected.value] != null).map(row => ({ date: row.recorded_on, value: row[selected.value]! })))
const weights = computed(() => shaping.data?.weight_history ?? [])
const composition = [{ metric: 'body_fat_percent', label: '体脂率', unit: '%', delta: '个百分点' }, { metric: 'skeletal_muscle_kg', label: '骨骼肌', unit: 'kg', delta: 'kg' }] as const
function delta(metric: 'body_fat_percent' | 'skeletal_muscle_kg', unit: string): string {
  const rows = shaping.measurements.filter(row => row[metric] != null)
  return signedDifference(rows.at(-1)?.[metric] ?? null, rows.at(-2)?.[metric] ?? null, unit)
}
</script>

<template>
  <article class="panel shape-panel">
    <div class="panel-head"><div><p class="eyebrow">BEYOND THE SCALE</p><h3>体重之外，看体成分</h3></div><button class="text-button" @click="$emit('record')">记录实测数据</button></div>
    <div class="shape-composition-grid">
      <div class="shape-metric-card shape-weight"><span>体重 · 来自身体档案</span><strong>{{ weights.at(-1)?.weight_kg.toFixed(1) ?? '未记录' }} <small v-if="weights.length">kg</small></strong><span>{{ signedDifference(weights.at(-1)?.weight_kg ?? null, weights.at(-2)?.weight_kg ?? null, 'kg') }}</span><small>{{ weights.at(-1)?.date ?? '等待首次记录' }}</small><button class="text-button" @click="$emit('weight')">管理体重 →</button></div>
      <button v-for="item in composition" :key="item.metric" class="shape-metric-card" :class="{ selected: selected === item.metric }" :aria-pressed="selected === item.metric" @click="selected = item.metric"><span>{{ item.label }} · 实测读数</span><strong>{{ shaping.latest(item.metric)?.[item.metric]?.toFixed(1) ?? '未记录' }} <small v-if="shaping.latest(item.metric)">{{ item.unit }}</small></strong><span>{{ delta(item.metric, item.delta) }}</span><small>{{ shaping.latest(item.metric)?.recorded_on ?? '不从 BMI 推算' }}</small><small v-if="shaping.latest(item.metric)?.composition_source">{{ SOURCE_LABELS[shaping.latest(item.metric)!.composition_source!] }}</small></button>
    </div>
    <MetricTrend :label="selected === 'body_fat_percent' ? '体脂率' : '骨骼肌'" :unit="selected === 'body_fat_percent' ? '%' : 'kg'" :entries="entries" />
    <p class="shape-muted">卡片变化均与该指标上一次实测值比较，测量日期可能不同。体脂秤受水分、进食及测量时段影响，尽量使用同一设备和条件；骨骼肌量与一般“肌肉量”不是同一指标。</p>
  </article>
</template>
