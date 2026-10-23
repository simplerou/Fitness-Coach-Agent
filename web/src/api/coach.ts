import { request } from './client'
import type { CoachAction, CoachAnswerResponse, CoachContext, CoachTurn } from './types'
export const askCoachAgent = (question: string, privacy_consent: boolean, context: CoachContext, history: CoachTurn[]) =>
  request<CoachAnswerResponse>('/api/shaping/intelligence/qa', {
    method: 'POST', body: JSON.stringify({ question, privacy_consent, context, history }),
  })
export const decideCoachAction = (id: number, decision: 'adopted' | 'ignored') =>
  request<{ ok: boolean; action: CoachAction; message: string }>('/api/shaping/intelligence/qa/actions/' + id, {
    method: 'PUT', body: JSON.stringify({ decision }),
  })
