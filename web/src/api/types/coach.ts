export interface CoachContext {
  page: 'today' | 'plan' | 'log' | 'diet' | 'shaping' | 'review' | 'library' | 'profile'
  selected_date: string | null
}
export interface CoachTurn { role: 'user' | 'assistant'; content: string }
export interface CoachAction {
  id: number; kind: 'diet_target' | 'plan_adjustment'; title: string; summary: string
  impact: string; details: string[]; target_date: string; status: 'pending' | 'adopted' | 'ignored'
}
export interface CoachAgentDetails {
  agent_mode: 'react' | 'local'
  tool_trace: Array<{ tool: string; label: string; status: 'success' | 'error'; summary: string }>
  stop_reason: 'complete' | 'tool_limit' | 'time_limit' | 'error'
  actions: CoachAction[]
  context_date: string
}
