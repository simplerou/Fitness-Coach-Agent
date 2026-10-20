<script setup lang="ts">
import { ref } from 'vue'
import ExerciseDetailDialog from './ExerciseDetailDialog.vue'
import ProgressionAdviceCard from './ProgressionAdviceCard.vue'
import { useTrainingStore } from '@/stores/training'
import type { ExerciseDefinition } from '@/api/types'

const emit = defineEmits<{ notice: [message: string] }>()
const store = useTrainingStore()
const active = ref<ExerciseDefinition | null>(null)
const completionLabels = { completed: '按计划完成', partial: '部分完成', skipped: '未进行训练' }
async function details(id: number): Promise<void> { active.value = store.exercises.find((item) => item.id === id) || null }
async function decide(id: number, decision: 'adopted' | 'ignored'): Promise<void> { emit('notice', await store.resolveAdvice(id, decision)) }
</script>

<template>
  <article class="panel training-history"><div class="panel-head"><div><p class="eyebrow">RECENT</p><h3>最近记录与进阶建议</h3></div><button class="text-button" type="button" :disabled="store.loading" @click="store.load">刷新</button></div>
    <div v-if="!store.logs.length" class="empty-state"><p>{{ store.loading ? '正在读取训练记录…' : '还没有训练记录。' }}</p></div>
    <article v-for="log in store.logs" :key="log.id" class="training-history-item">
      <div class="training-history-head"><b>{{ log.training_date }} · {{ completionLabels[log.completion] }}</b><span>{{ log.rpe == null ? '整场 RPE 未记录' : `整场 RPE ${log.rpe}` }}</span></div>
      <div v-if="log.exercises.length" class="logged-exercises"><button v-for="item in log.exercises" :key="item.id" type="button" @click="details(item.exercise_id)"><b>{{ item.exercise_name }}</b><span>{{ item.sets }} 组 × {{ item.reps }} 次 · {{ item.weight_kg }} kg · RPE {{ item.rpe }}</span></button></div>
      <p v-else class="fine-print">旧记录：未记录动作明细。</p>
      <div v-if="log.recovery" class="logged-recovery" :class="`status-${log.recovery.status}`"><b>恢复：{{ log.recovery.status }}</b><span>{{ log.recovery.message }}</span></div>
      <ProgressionAdviceCard v-for="advice in log.advice" :key="advice.id" :advice="advice" @decide="decide" />
    </article>
    <ExerciseDetailDialog :exercise="active" @close="active = null" />
  </article>
</template>
