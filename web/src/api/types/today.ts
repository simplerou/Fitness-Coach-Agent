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

