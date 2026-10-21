import type { Readiness } from './today'
import type { LogCompletion, SkipReason } from './training'

export interface ReviewSummary {
  session_count: number; completed_count: number; partial_count: number; skipped_count: number
  average_rpe: number | null; rpe_count: number; planned_day_count: number; planned_elapsed_day_count: number
  planned_completed_count: number; planned_partial_count: number; planned_skipped_count: number; planned_unlogged_count: number
  diet_meal_count: number; diet_days_with_meals: number; diet_days_marked_complete: number
  diet_water_days_logged: number; diet_water_total_ml: number | null; weight_days_logged: number
}
export interface ReviewDay {
  date: string; before_registration: boolean; plan_status: string; planned_session_title: string | null
  is_planned_training_day: boolean
  signal: { readiness: Readiness; sleep_hours: number | null; resting_hr: number | null } | null
  logs: Array<{ completion: LogCompletion; rpe: number | null; skip_reason: SkipReason | null; note: string | null; planned_session_title: string | null }>
  diet: { meals: Array<{ meal_type: string; description: string }>; meal_count: number; calories_kcal: number | null; calories_logged_count: number; protein_g: number | null; carbs_g: number | null; fat_g: number | null; water_ml: number | null; complete: boolean | null }
  weight_kg: number | null
}
export interface WeeklyReviewResponse { week_start: string; week_end: string; registration_date: string; summary: ReviewSummary; days: ReviewDay[] }

