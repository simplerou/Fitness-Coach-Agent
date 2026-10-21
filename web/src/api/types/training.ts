import type { PlanSessionItem, WeekPlan } from './plan'

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

