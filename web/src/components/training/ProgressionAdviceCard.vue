<script setup lang="ts">
import type { ProgressionAdvice } from '@/api/types'
defineProps<{ advice: ProgressionAdvice }>()
defineEmits<{ decide: [id: number, decision: 'adopted' | 'ignored'] }>()
const typeLabels = { weight: '加重', reps: '加次数', sets: '加组' }
</script>

<template>
  <article class="progression-card">
    <div><span class="tag">{{ typeLabels[advice.advice_type] }}</span><b>{{ advice.exercise_name }}</b><span v-if="advice.status !== 'pending'" class="advice-status">{{ advice.status === 'adopted' ? '已采纳' : '已忽略' }}</span></div>
    <p class="progression-prescription">建议 {{ advice.prescription.sets }} 组 × {{ advice.prescription.reps }} 次<span v-if="advice.prescription.weight_kg > 0"> · {{ advice.prescription.weight_kg }} kg</span></p>
    <p>{{ advice.reason }}</p>
    <details><summary>查看依据记录</summary><ul><li v-for="(row, index) in advice.evidence" :key="index">{{ row.training_date }} · {{ row.sets }} 组 × {{ row.reps }} 次 · {{ row.weight_kg }} kg · RPE {{ row.rpe }}</li></ul></details>
    <div v-if="advice.status === 'pending'" class="advice-actions"><button class="button button-primary" type="button" @click="$emit('decide', advice.id, 'adopted')">采纳</button><button class="button button-quiet" type="button" @click="$emit('decide', advice.id, 'ignored')">忽略</button></div>
  </article>
</template>
