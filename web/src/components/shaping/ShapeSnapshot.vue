<script setup lang="ts">
import { computed } from 'vue'
import { useShapingStore } from '@/stores/shaping'
import { SHAPE_LABELS, SHAPE_UNITS } from '@/constants/shaping'
import type { ShapeMetric } from '@/api/types'
const props = defineProps<{ date: string }>()
const shaping = useShapingStore()
const record = computed(() => shaping.measurements.find(row => row.recorded_on === props.date))
const weight = computed(() => shaping.data?.weight_history.find(row => row.date === props.date)?.weight_kg)
const metrics: ShapeMetric[] = ['waist_cm', 'hip_cm', 'chest_cm', 'arm_cm', 'thigh_cm', 'body_fat_percent', 'skeletal_muscle_kg']
</script>

<template>
  <div class="shape-snapshot"><p><b>{{ date }}</b> · 同日测量</p><div><span>体重 <strong>{{ weight == null ? '未记录' : `${weight} kg` }}</strong></span><span v-for="metric in metrics" :key="metric">{{ SHAPE_LABELS[metric] }} <strong>{{ record?.[metric] == null ? '未记录' : `${record[metric]} ${SHAPE_UNITS[metric]}` }}</strong></span></div><small>仅展示这一天的实测数据，不用其他日期补齐。</small></div>
</template>
