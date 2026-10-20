import { request } from '@/api/client'
import type { DietFood, DietLogResponse, DietMealPayload, DietProfile, DietPlanData, DietPlanHistoryItem, DietTargetsResponse } from '@/api/types'

export const getDietProfile = (): Promise<{ profile: DietProfile | null }> => request('/api/diet/profile')
export const saveDietProfile = (profile: DietProfile): Promise<{ ok: boolean; message: string }> => request('/api/diet/profile', { method: 'PUT', body: JSON.stringify(profile) })
export const getDietTargets = (): Promise<DietTargetsResponse> => request('/api/diet/targets')
export function getDietLog(date: string): Promise<DietLogResponse> { return request(`/api/diet?log_date=${encodeURIComponent(date)}`) }
export function searchFoods(keyword: string): Promise<{ items: DietFood[]; source: string }> { return request(`/api/diet/foods/search?keyword=${encodeURIComponent(keyword)}`) }
export function getFoodDetail(code: string): Promise<{ food: DietFood; source: string }> { return request(`/api/diet/foods/detail?code=${encodeURIComponent(code)}`) }
export function saveMeal(payload: DietMealPayload, mealId: number | null): Promise<{ ok: boolean; meal: unknown; message: string }> {
  return request(mealId == null ? '/api/diet/meal' : `/api/diet/meal/${mealId}`, { method: mealId == null ? 'POST' : 'PUT', body: JSON.stringify(payload) })
}
export function deleteMeal(mealId: number): Promise<{ ok: boolean; message: string }> { return request(`/api/diet/meal/${mealId}`, { method: 'DELETE' }) }
export function addWater(date: string, amount_ml: number): Promise<{ ok: boolean; water_ml: number; message: string }> {
  return request('/api/diet/water', { method: 'POST', body: JSON.stringify({ log_date: date, amount_ml }) })
}
export function updateDietDayReview(date: string, complete: boolean): Promise<{ ok: boolean; complete: boolean; message: string }> {
  const params = new URLSearchParams({ log_date: date, complete: String(complete) })
  return request(`/api/diet/day-review?${params}`, { method: 'PUT' })
}
export function createDietPlan(): Promise<DietPlanData> { return request('/api/diet/plan', { method: 'POST', body: JSON.stringify({ privacy_consent: true }) }) }
export function getDietPlanHistory(): Promise<{ items: DietPlanHistoryItem[] }> { return request('/api/diet/plan/history') }
