import { request } from '@/api/client'
import type { LogsResponse, PlanSessionDateResponse, TrainingLogPayload, TrainingLogResponse } from '@/api/types'

export const getLogs = (): Promise<LogsResponse> => request('/api/logs')
export function getPlanSession(trainingDate: string): Promise<PlanSessionDateResponse> {
  return request(`/api/plan/session?training_date=${encodeURIComponent(trainingDate)}`)
}
export function createLog(payload: TrainingLogPayload): Promise<TrainingLogResponse> {
  return request('/api/log', { method: 'POST', body: JSON.stringify(payload) })
}
