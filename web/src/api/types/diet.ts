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
