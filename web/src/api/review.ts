import { request } from '@/api/client'
import type { WeeklyReviewResponse } from '@/api/types'

export function getWeeklyReview(weekOf: string): Promise<WeeklyReviewResponse> {
  return request(`/api/review/week?week_of=${encodeURIComponent(weekOf)}`)
}
