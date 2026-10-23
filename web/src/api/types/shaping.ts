import type { CoachAgentDetails } from './coach'
import type { WeightHistoryItem } from './plan'

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

export type MuscleGroup = '胸' | '背' | '腿' | '肩' | '臂' | '核心'
export interface ShapingIntelligencePreferences {
  goal: 'whole_body' | 'glutes_legs' | 'shoulders_back'
  focus_groups: MuscleGroup[]
  excluded_groups: MuscleGroup[]
}
export interface MuscleGroupStat {
  muscle_group: MuscleGroup; frequency: number; total_sets: number; coverage_percent: number
  period_start: string; period_end: string
}
export interface WeakPartAdvice {
  id: number; status: 'pending' | 'adopted' | 'ignored'; muscle_group: MuscleGroup; evidence: string
  exercises: Array<{ id: number; name: string; category: string; target_muscles: string[] }>
  prescription: string; target_weekday: number | null; target_day_label: string; integration: string
}
export interface WeakPartAnalysis {
  status: 'ready' | 'insufficient_data'; message: string; period_start: string; period_end: string
  observed_weeks: number; mean_coverage_percent?: number; stats: MuscleGroupStat[]
  advice: WeakPartAdvice[]; preferences: ShapingIntelligencePreferences
}
export interface CoachExerciseReference {
  id: number; slug: string; name: string; category: string; target_muscles: string[]; cues: string[]
  common_errors: Array<{ error: string; correction: string }>; regressions: string[]; progressions: string[]
  alternatives: Array<{ name: string; scene: string }>; demo_images: string[]; demo_video_url: string | null
}
export interface CoachAnswerResponse extends CoachAgentDetails {
  intent: 'medical' | 'substitution' | 'technique' | 'schedule'; answer: string; safety_note: string | null
  referenced_exercise_ids: number[]; references: CoachExerciseReference[]; used_llm: boolean; model_note: string
  referenced_source_keys: string[]; cited_source_keys: string[]; retrieval_method: string; retrieval_note: string | null
  embedding_model: string; vector_model_used: boolean
  knowledge_sources: Array<{ document_key: string; title: string; source_name: string; source_url: string | null
    source_published_at: string | null; retrieved_at: string; excerpt: string; retrieval_channels: string[]
    bm25_score: number; vector_score: number | null }>
}
export interface DietDayAdjustment {
  status: 'proposed' | 'adopted' | 'ignored' | 'needs_data' | 'professional_support' | 'data_conflict'
  date: string; day_type?: 'training' | 'rest' | 'recovery'; intensity?: 'high' | 'regular' | 'rest' | 'recovery'
  message?: string; missing?: string[]; suggestion?: {
    calories_kcal: number; protein_g: number; carbs_g: number; fat_g: number; basis_calories_kcal: number
    reason: string; calculation: string
  }
}
export interface ShapeReportData {
  period_type: 'week' | 'month'; period_start: string; period_end: string
  sample_status: 'sufficient' | 'insufficient'; data_notes: string[]
  measurements: { changes: Array<{ metric: ShapeMetric; label: string; current: number | null; previous: number | null; change: number | null; measurement_count: number; current_date: string | null; previous_date: string | null }>; record_count: number; trend: Array<{ recorded_on: string } & Record<ShapeMetric, number | null>>; source: string }
  weight: { change_kg: number | null; record_count: number; source: string }
  training: { training_days: number; log_count: number; total_sets: number; total_reps: number; completion_rate: number | null; source: string }
  performance: { highlights: Array<{ exercise: string; type: string; status: string; reason: string }>; milestones: Array<{ metric: string; label: string; milestones: number[] }>; source: string }
  recovery: { checkin_count: number; average_soreness: number | null; average_sleep_hours: number | null; insufficient_days: number; source: string }
  weak_part_progress: Array<{ muscle_group: MuscleGroup; status: string; evidence: string; integration: string }>
  next_actions: string[]
}
export interface ShapeReportSnapshot {
  id: number; period_type: 'week' | 'month'; period_start: string; period_end: string; generated_at: string; report: ShapeReportData
}

