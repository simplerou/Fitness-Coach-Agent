import { request } from '@/api/client'
import type { CurrentPlanResponse, GeneratePlanResponse, PlanHistoryResponse, PlanPreferences, PlanPreferencesResponse } from '@/api/types'

export const getPlanPreferences = (): Promise<PlanPreferencesResponse> => request('/api/plan/preferences')
export const getCurrentPlan = (): Promise<CurrentPlanResponse> => request('/api/plan/current')
export function getPlanHistory(limit = 20, before_week_start: string | null = null): Promise<PlanHistoryResponse> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (before_week_start) params.set('before_week_start', before_week_start)
  return request(`/api/plan/history?${params.toString()}`)
}
export function generatePlan(preferences: PlanPreferences): Promise<GeneratePlanResponse> {
  return request('/api/plan', { method: 'POST', body: JSON.stringify(preferences) })
}
