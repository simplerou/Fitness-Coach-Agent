import { reactive, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { useAuthStore } from './auth'
import { askCoachAgent } from '@/api/coach'
import type { CoachContext, CoachTurn } from '@/api/types'
import * as api from '@/api/shapingIntelligence'
import type { CoachAnswerResponse, DietDayAdjustment, ShapeReportSnapshot, ShapingIntelligencePreferences, WeakPartAnalysis } from '@/api/types'

export const useShapingIntelligenceStore = defineStore('shaping-intelligence', () => {
  const auth = useAuthStore()
  const preferences = reactive<ShapingIntelligencePreferences>({ goal: 'whole_body', focus_groups: [], excluded_groups: [] })
  const weakAnalysis = ref<WeakPartAnalysis | null>(null)
  const coachAnswer = ref<CoachAnswerResponse | null>(null)
  const dietAdjustment = ref<DietDayAdjustment | null>(null)
  const reports = ref<ShapeReportSnapshot[]>([])
  const reportTrigger = ref('')
  const loading = ref(false)
  const asking = ref(false)
  let askVersion = 0
  const error = ref('')

  watch(() => auth.user?.id, () => {
    askVersion += 1; asking.value = false
    weakAnalysis.value = null; coachAnswer.value = null; dietAdjustment.value = null; reports.value = []; error.value = ''
    Object.assign(preferences, { goal: 'whole_body', focus_groups: [], excluded_groups: [] })
  })

  async function loadPreferences(): Promise<void> { Object.assign(preferences, (await api.getIntelligencePreferences()).preferences) }
  async function savePreferences(): Promise<string> {
    const result = await api.saveIntelligencePreferences({ ...preferences })
    Object.assign(preferences, result.preferences); return result.message
  }
  async function analyze(): Promise<void> {
    loading.value = true; error.value = ''
    try { weakAnalysis.value = await api.analyzeWeakParts() }
    catch (cause) { error.value = cause instanceof Error ? cause.message : '薄弱部位分析暂时不可用。'; throw cause }
    finally { loading.value = false }
  }
  async function decideWeak(id: number, decision: 'adopted' | 'ignored'): Promise<string> {
    const result = await api.decideWeakPart(id, decision)
    const item = weakAnalysis.value?.advice.find(row => row.id === id)
    if (item) item.status = decision
    return result.message
  }
  async function undoWeak(id: number): Promise<string> {
    const result = await api.resetWeakPartDecision(id)
    const item = weakAnalysis.value?.advice.find(row => row.id === id)
    if (item) item.status = 'pending'
    return result.message
  }
  async function ask(question: string, consent: boolean, context: CoachContext = { page: 'today', selected_date: null },
    history: CoachTurn[] = []): Promise<CoachAnswerResponse | null> {
    const version = ++askVersion
    asking.value = true
    try {
      const answer = await askCoachAgent(question, consent, context, consent ? history : [])
      if (version !== askVersion) return null
      coachAnswer.value = answer
      return answer
    } catch (cause) {
      if (version !== askVersion) return null
      throw cause
    } finally { if (version === askVersion) asking.value = false }
  }
  async function loadDietAdjustment(date: string): Promise<void> { dietAdjustment.value = await api.getDietAdjustment(date) }
  async function decideDiet(date: string, decision: 'adopted' | 'ignored'): Promise<string> {
    const result = await api.decideDietAdjustment(date, decision)
    if (dietAdjustment.value?.date === date) dietAdjustment.value.status = decision
    return result.message
  }
  async function loadReports(): Promise<void> {
    const result = await api.getAutoShapeReports(); reports.value = result.items; reportTrigger.value = result.trigger
  }
  return { preferences, weakAnalysis, coachAnswer, dietAdjustment, reports, reportTrigger, loading, asking, error,
    loadPreferences, savePreferences, analyze, decideWeak, undoWeak, ask, loadDietAdjustment, decideDiet, loadReports }
})
