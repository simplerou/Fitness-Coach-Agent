export type ShapeCircumference = 'waist_cm' | 'hip_cm' | 'chest_cm' | 'arm_cm' | 'thigh_cm'
export type ShapeMetric = ShapeCircumference | 'body_fat_percent' | 'skeletal_muscle_kg'
export type ShapeTargetMetric = Exclude<ShapeMetric, 'skeletal_muscle_kg'>
export type ShapePhotoView = 'front' | 'side' | 'back'
export type ShapeSource = 'scale_reading' | 'professional_measurement' | 'manual'
export interface ShapeMeasurementPayload extends Record<ShapeMetric, number | null> {
  recorded_on: string
  composition_source: ShapeSource | null
}
export interface ShapeMeasurement extends ShapeMeasurementPayload { weight_kg: number | null }
export interface ShapeTarget {
  metric: ShapeTargetMetric
  baseline_value: number
  baseline_date: string
  target_value: number
  current_value: number | null
  current_date: string | null
  progress_percent: number | null
  milestones: number[]
}
export interface ShapePhoto {
  id: number
  recorded_on: string
  view: ShapePhotoView
  updated_at: string
}
export interface ShapeDashboard {
  today: string
  measurements: ShapeMeasurement[]
  weight_history: WeightHistoryItem[]
  reminders: { metric: ShapeCircumference; last_measured_on: string | null; next_due_on: string | null; due: boolean }[]
  targets: ShapeTarget[]
  photos: ShapePhoto[]
}
export interface ShapeMutationResult { ok: boolean; message: string; milestone_messages?: string[] }

export interface AuthUser {
  id: number
  username: string
  display_name: string
}

export interface AuthResponse {
  user: AuthUser
}

export interface AuthLogoutResponse {
  ok: boolean
}

export interface RegisterPayload {
  username: string
  password: string
  display_name: string | null
}

export interface LoginPayload {
  username: string
  password: string
}

export interface ErrorResponse {
  detail: string | null
}

export type SafetyStatus = 'ask' | 'clear' | 'stop'
export type TodayLevel = 'ask' | 'stop' | 'insufficient_data' | 'normal' | 'rest_day' | 'downgrade'
export type Readiness = 'good' | 'okay' | 'poor'

export interface TodaySession {
  title: string
  description: string
  duration_minutes: number | null
  [key: string]: unknown
}

export interface TodaySchedule {
  status: 'training' | 'rest' | 'legacy_plan' | 'no_plan'
  weekday: number
  message: string
  session: TodaySession | null
}

export interface TodayResponse {
  level: TodayLevel
  screening_date?: string | null
  message: string
  today_schedule?: TodaySchedule | null
  plan_items: TodaySession[]
  reasons: string[]
}

export interface SafetyCheckPayload {
  completed: boolean
  no_symptoms: boolean
  symptoms: string[]
}

export interface SafetyCheckResponse {
  status: SafetyStatus
  screening_date: string | null
  message: string
  symptoms: string[]
}

export interface DailySignalPayload {
  readiness: Readiness
  sleep_hours: number | null
  resting_hr: number | null
}

export interface DailySignalResponse {
  accepted: boolean
  source: string
  recorded_at: string
  message: string
}

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
  exercises?: Array<{ id: number; name: string; category: string; target_muscles: string[] }>
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

export type LogCompletion = 'completed' | 'partial' | 'skipped'
export type SkipReason = 'no_time' | 'too_tired' | 'discomfort' | 'other'
export interface TrainingLogPayload { training_date: string; completion: LogCompletion; rpe: number | null; skip_reason: SkipReason | null; note: string | null }
export interface TrainingLogItem { training_date: string; completion: LogCompletion; rpe: number | null; skip_reason: SkipReason | null; note: string | null; planned_session_title: string | null }
export interface LogsResponse { items: TrainingLogItem[] }
export interface PlanSessionDateResponse { training_date: string; status: 'training' | 'rest' | 'legacy_plan' | 'no_plan' | 'before_registration'; session: PlanSessionItem | null; weekday?: number; message?: string }
export interface TrainingLogResponse { ok: boolean; log: TrainingLogPayload & { planned_session_title: string | null }; message: string }

export interface ExerciseDefinition {
  id: number; slug: string; name: string; category: string; target_muscles: string[]; equipment: string[]
  cues: string[]; common_errors: Array<{ error: string; correction: string }>; regressions: string[]
  progressions: string[]; alternatives: Array<{ name: string; scene: string }>
  demo_images: string[]; demo_video_url: string | null; media_credit: string | null
  media_license: string | null; media_source_url: string | null
}
export interface ExerciseEntryPayload {
  exercise_id: number; sets: number; reps: number; target_reps_min: number; target_reps_max: number
  weight_kg: number; rpe: number; completion: LogCompletion
}
export interface RecoveryPayload {
  soreness: number; sleep_hours: number; sleep_quality: number; energy: number; is_sick: boolean
  warning_symptom: 'none' | 'joint_pain' | 'sharp_pain' | 'swelling'; note: string | null
}
export interface ProgressionAdvice {
  id: number; exercise_id: number; exercise_name: string; advice_type: 'weight' | 'reps' | 'sets'
  prescription: { sets: number; reps: number; weight_kg: number }; evidence: Array<Record<string, string | number>>
  reason: string; status: 'pending' | 'adopted' | 'ignored'; created_at: string
}
export interface RecoveryResult extends RecoveryPayload { status: 'good' | 'attention' | 'insufficient' | 'rest' | 'stop'; message: string }
export interface DetailedTrainingLog extends TrainingLogItem {
  id: number; exercises: Array<ExerciseEntryPayload & { id: number; exercise_name: string }>
  recovery: RecoveryResult | null; advice: ProgressionAdvice[]
}
export interface SmartTrainingLogPayload extends TrainingLogPayload { exercises: ExerciseEntryPayload[]; recovery: RecoveryPayload | null }
export interface SmartTrainingLogResponse { ok: boolean; log_id: number; message: string; recovery: { status: string; message: string; allow_progression: boolean } | null; advice: ProgressionAdvice[] }
export interface RecoverySummary { today: { status: string; message: string } | null; week: { status: string; message: string; checkin_count: number } | null }
export interface PlanAdjustment {
  id: number; source_week_start: string; target_week_start: string; status: 'pending' | 'adopted' | 'ignored'
  recommendation: { kind: string; changed: string[]; reasons: string[]; unchanged: string[]; proposed_plan: WeekPlan; stats: Record<string, unknown> }
}

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

export type DietMealType = 'breakfast' | 'lunch' | 'dinner' | 'snack'
export interface DietMeal {
  id: number; log_date?: string; meal_type: DietMealType; description: string; note: string | null; portion: string | null
  eaten_at: string | null; calories_kcal: number | null; protein_g: number | null; carbs_g: number | null; fat_g: number | null
  nutrition_source: 'label' | 'estimate' | null; created_at?: string | null
}
export interface DietLogResponse { log_date: string; items: DietMeal[]; water_ml: number; day_complete: boolean }
export interface DietMealPayload {
  log_date: string; meal_type: DietMealType; description: string; note: string | null; portion: string | null; eaten_at: string | null
  calories_kcal: number | null; protein_g: number | null; carbs_g: number | null; fat_g: number | null; nutrition_source: 'label' | 'estimate' | null
}
export interface DietProfile {
  goal: 'fat_loss' | 'muscle_gain' | 'maintain' | 'body_shape' | 'performance' | null
  activity_level: 'sedentary' | 'light' | 'moderate' | 'active' | 'very_active' | null
  training_type: 'strength' | 'cardio' | 'mixed' | 'other' | null
  training_time: string | null; training_end_time: string | null; dietary_preference: string | null; allergies: string | null
  allergies_reviewed: boolean; avoid_foods: string | null; medical_conditions: string | null; injuries: string | null; health_reviewed: boolean
  cooking_access: 'none' | 'basic' | 'full' | null; eating_out_per_week: number | null; budget_note: string | null; water_target_ml: number | null
}
export interface DietProfileResponse { profile: DietProfile | null }
export interface DietTargetsResponse {
  status: string; message: string; missing?: string[]; summary?: Record<string, string | number | null>
  target?: { calories_kcal: number; protein_g: number; carbs_g: number; fat_g: number; protein_percent: number; carbs_percent: number; fat_percent: number; basis: string }
  hydration?: { target_ml: number | null; suggested_ml: number | null; source: string; basis: string | null; note: string | null }
  warnings?: string[]
}
export interface DietFood { [key: string]: unknown }
export interface DietSelectedFood { name: string; id: string | number; per100: boolean; grams: number; macros: { calories_kcal: number | null; protein_g: number | null; carbs_g: number | null; fat_g: number | null } }
export interface DietPlanData {
  status: string; message: string; missing?: string[]; summary?: Record<string, unknown>; target?: Record<string, unknown>
  record_summary?: Record<string, any>; ai_advice?: Record<string, any>; diagnosis?: string[]; warnings?: string[]; assumptions?: string[]
  weekly_plan?: Array<Record<string, any>>; meal_plan?: Array<Record<string, any>>; food_examples?: Array<Record<string, any>>
  recorded_habits?: Record<string, string>; execution_context?: Record<string, unknown>; tracking?: Record<string, any>; change_summary?: string
  [key: string]: unknown
}
export interface DietPlanHistoryItem { id: number; generated_on: string; created_at: string; plan_data: DietPlanData }
