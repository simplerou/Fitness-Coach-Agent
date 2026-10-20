import { request } from '@/api/client'
import type {
  CurrentPlanResponse,
  DailySignalPayload,
  DailySignalResponse,
  SafetyCheckPayload,
  SafetyCheckResponse,
  TodayResponse,
} from '@/api/types'

export function getToday(): Promise<TodayResponse> {
  return request<TodayResponse>('/api/today')
}

export function submitSafetyCheck(payload: SafetyCheckPayload): Promise<SafetyCheckResponse> {
  return request<SafetyCheckResponse>('/api/safety-check', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function saveDailySignal(payload: DailySignalPayload): Promise<DailySignalResponse> {
  return request<DailySignalResponse>('/api/daily-signal', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getCurrentPlan(): Promise<CurrentPlanResponse> {
  return request<CurrentPlanResponse>('/api/plan/current')
}
