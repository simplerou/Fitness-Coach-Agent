import { request } from '@/api/client'
import type { DetailedTrainingLog, ExerciseDefinition, PlanAdjustment, RecoverySummary, SmartTrainingLogPayload, SmartTrainingLogResponse } from '@/api/types'

export function getExercises(q = '', muscle = '', equipment = ''): Promise<{ items: ExerciseDefinition[]; total: number }> {
  const params = new URLSearchParams()
  if (q) params.set('q', q)
  if (muscle) params.set('muscle', muscle)
  if (equipment) params.set('equipment', equipment)
  return request(`/api/training/exercises?${params}`)
}
export const getExercise = (id: number): Promise<ExerciseDefinition> => request(`/api/training/exercises/${id}`)
export const createSmartTrainingLog = (payload: SmartTrainingLogPayload): Promise<SmartTrainingLogResponse> =>
  request('/api/training/logs', { method: 'POST', body: JSON.stringify(payload) })
export const getDetailedTrainingLogs = (): Promise<{ items: DetailedTrainingLog[] }> => request('/api/training/logs')
export const decideAdvice = (id: number, decision: 'adopted' | 'ignored'): Promise<{ message: string }> =>
  request(`/api/training/advice/${id}`, { method: 'PUT', body: JSON.stringify({ decision }) })
export const getRecoverySummary = (): Promise<RecoverySummary> => request('/api/training/recovery/summary')
export const previewPlanAdjustment = (weekOf: string): Promise<PlanAdjustment> =>
  request(`/api/training/adjustments/preview?week_of=${encodeURIComponent(weekOf)}`, { method: 'POST' })
export const decidePlanAdjustment = (id: number, decision: 'adopted' | 'ignored'): Promise<{ message: string }> =>
  request(`/api/training/adjustments/${id}`, { method: 'PUT', body: JSON.stringify({ decision }) })
