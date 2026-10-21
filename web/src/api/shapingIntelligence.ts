import { request } from './client'
import type { CoachAnswerResponse, DietDayAdjustment, ShapeReportSnapshot, ShapingIntelligencePreferences, WeakPartAnalysis } from './types'

export const getIntelligencePreferences = () => request<{ preferences: ShapingIntelligencePreferences }>('/api/shaping/intelligence/preferences')
export const saveIntelligencePreferences = (payload: ShapingIntelligencePreferences) => request<{ ok: boolean; message: string; preferences: ShapingIntelligencePreferences }>(
  '/api/shaping/intelligence/preferences', { method: 'PUT', body: JSON.stringify(payload) })
export const analyzeWeakParts = () => request<WeakPartAnalysis>('/api/shaping/intelligence/weak-parts/analyze', { method: 'POST' })
export const decideWeakPart = (id: number, decision: 'adopted' | 'ignored') => request<{ ok: boolean; status: string; message: string }>(
  `/api/shaping/intelligence/weak-parts/${id}`, { method: 'PUT', body: JSON.stringify({ decision }) })
export const resetWeakPartDecision = (id: number) => request<{ ok: boolean; status: string; message: string }>(
  `/api/shaping/intelligence/weak-parts/${id}/decision`, { method: 'DELETE' })
export const askCoach = (question: string, privacy_consent: boolean) => request<CoachAnswerResponse>(
  '/api/shaping/intelligence/qa', { method: 'POST', body: JSON.stringify({ question, privacy_consent }) })
export const getDietAdjustment = (date: string) => request<DietDayAdjustment>(
  `/api/shaping/intelligence/diet-adjustment?date=${encodeURIComponent(date)}`)
export const decideDietAdjustment = (date: string, decision: 'adopted' | 'ignored') => request<{ ok: boolean; status: string; message: string }>(
  `/api/shaping/intelligence/diet-adjustment/${date}`, { method: 'PUT', body: JSON.stringify({ decision }) })
export const getAutoShapeReports = () => request<{ items: ShapeReportSnapshot[]; trigger: string }>('/api/shaping/intelligence/reports/auto')
export const getShapeReports = (period?: 'week' | 'month') => request<{ items: ShapeReportSnapshot[] }>(
  `/api/shaping/intelligence/reports${period ? `?period_type=${period}` : ''}`)
