import { request } from '@/api/client'
import type { BodyProfilePayload, BodyProfileResponse } from '@/api/types'

export function getBodyProfile(): Promise<BodyProfileResponse> {
  return request<BodyProfileResponse>('/api/body-profile')
}

export function saveBodyProfile(payload: BodyProfilePayload): Promise<{ ok: boolean; updated_at: string; message: string }> {
  return request('/api/body-profile', { method: 'PUT', body: JSON.stringify(payload) })
}

export function deleteBodyProfile(): Promise<{ ok: boolean; message: string }> {
  return request('/api/body-profile', { method: 'DELETE' })
}

export function saveBodyWeight(weight_kg: number): Promise<{ ok: boolean; recorded_on: string; weight_kg: number; message: string }> {
  return request('/api/body-weight', { method: 'POST', body: JSON.stringify({ weight_kg }) })
}

export function saveWeightTarget(target_weight_kg: number | null): Promise<{ ok: boolean; target_weight_kg: number | null; message: string }> {
  return request('/api/body-profile/target-weight', { method: 'PUT', body: JSON.stringify({ target_weight_kg }) })
}
