import { ref } from 'vue'
import { defineStore } from 'pinia'
import { decideAdvice, getDetailedTrainingLogs, getExercises, getRecoverySummary, resetAdviceDecision } from '@/api/training'
import type { DetailedTrainingLog, ExerciseDefinition, RecoverySummary } from '@/api/types'

export const useTrainingStore = defineStore('training', () => {
  const exercises = ref<ExerciseDefinition[]>([])
  const logs = ref<DetailedTrainingLog[]>([])
  const recovery = ref<RecoverySummary>({ today: null, week: null })
  const loading = ref(false)

  async function loadExercises(query = ''): Promise<void> { exercises.value = (await getExercises(query)).items }
  async function load(): Promise<void> {
    loading.value = true
    try {
      const [logResult, recoveryResult] = await Promise.all([getDetailedTrainingLogs(), getRecoverySummary()])
      logs.value = logResult.items; recovery.value = recoveryResult
    } finally { loading.value = false }
  }
  async function resolveAdvice(id: number, decision: 'adopted' | 'ignored'): Promise<string> {
    const result = await decideAdvice(id, decision)
    const advice = logs.value.flatMap((row) => row.advice).find((row) => row.id === id)
    if (advice) advice.status = decision
    return result.message
  }
  async function undoAdvice(id: number): Promise<string> {
    const result = await resetAdviceDecision(id)
    const advice = logs.value.flatMap((row) => row.advice).find((row) => row.id === id)
    if (advice) advice.status = 'pending'
    return result.message
  }
  return { exercises, logs, recovery, loading, loadExercises, load, resolveAdvice, undoAdvice }
})
