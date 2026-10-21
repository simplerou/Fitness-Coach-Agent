export interface PlanSession {
  title: string
  description: string
  duration_minutes: number | null
  [key: string]: unknown
}

export interface CurrentPlanResponse {
  week_plan: Record<string, unknown> | null
  week_start: string
  saved_at: string | null
}

export interface BodyProfile {
  age_band: string
  age_years: number
  biological_sex: 'female' | 'male' | 'unspecified' | null
  height_cm: number
  weight_kg: number
  target_weight_kg: number | null
  updated_at: string
}

export interface WeightHistoryItem {
  date: string
  weight_kg: number
}

export interface BodyProfileResponse {
  profile: BodyProfile | null
  weight_history: WeightHistoryItem[]
  legacy_demographics: { age_years: number | null; biological_sex: BodyProfile['biological_sex'] } | null
}

export interface BodyProfilePayload {
  age_years: number
  biological_sex: BodyProfile['biological_sex']
  height_cm: number
  weight_kg: number
}

export interface PlanPreferences {
  goal: 'strength' | 'fitness' | 'fat_loss'
  days_per_week: number
  training_weekdays: number[]
  experience_level: 'beginner' | 'some_experience' | 'experienced'
  equipment: Array<'bodyweight_only' | 'dumbbells' | 'resistance_bands' | 'gym'>
  session_minutes: 20 | 30 | 45 | 60
  preferred_exercise_ids: number[]
}

export interface PlanSessionItem {
  weekday: number
  day: string
  title: string
  description: string
  duration_minutes: number
  exercises?: Array<{ id: number; name: string; category: string; target_muscles: string[]; sets?: number; reps_range?: string; source?: string }>
  [key: string]: unknown
}

export interface WeekPlan {
  goal: PlanPreferences['goal']
  focus: string
  days_per_week: number
  training_weekdays: number[]
  rest_weekdays: number[]
  experience_level: PlanPreferences['experience_level']
  equipment: PlanPreferences['equipment']
  session_minutes: number
  sessions: PlanSessionItem[]
  body_profile_context: { personal_profile_used: boolean; height_cm: number | null; weight_kg: number | null; target_weight_kg: number | null }
  notice: string
  [key: string]: unknown
}

export interface PlanPreferencesResponse { preferences: PlanPreferences; updated_at: string }
export interface PlanHistoryItem { week_start: string; week_end: string; saved_at: string; week_plan: WeekPlan }
export interface PlanHistoryResponse {
  current_week_start: string
  items: PlanHistoryItem[]
  next_before_week_start: string | null
  has_more: boolean
}
export interface GeneratePlanResponse { week_plan: WeekPlan; week_start: string; saved_at: string; message: string }

