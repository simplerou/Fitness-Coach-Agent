import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { ApiError } from '@/api/client'
import { getToday, saveDailySignal, submitSafetyCheck } from '@/api/today'
import type { DailySignalPayload, Readiness, SafetyStatus, TodayLevel, TodayResponse } from '@/api/types'
import { localDateString } from '@/utils/date'

export const useSafetyStore = defineStore('safety', () => {
  const safetyStatus = ref<SafetyStatus | 'loading'>('loading')
  const screeningDate = ref<string | null>(null)
  const today = ref<TodayResponse | null>(null)
  const loading = ref(false)
  const submittingCheck = ref(false)
  const submittingSignal = ref(false)
  const errorMessage = ref<string | null>(null)
  const isRestDay = computed(() => today.value?.level === 'rest_day')

  function updateFromToday(result: TodayResponse): void {
    today.value = result
    safetyStatus.value = result.level === 'ask' ? 'ask' : result.level === 'stop' ? 'stop' : 'clear'
    screeningDate.value = result.screening_date ?? null
  }

  async function refreshToday(): Promise<void> {
    loading.value = true
    errorMessage.value = null
    try {
      updateFromToday(await getToday())
    } catch (error) {
      safetyStatus.value = 'loading'
      screeningDate.value = null
      errorMessage.value = error instanceof Error ? error.message : '请求失败，请稍后重试。'
    } finally {
      loading.value = false
    }
  }

  async function submitCheck(noSymptoms: boolean): Promise<void> {
    if (safetyStatus.value === 'stop' || submittingCheck.value) return
    submittingCheck.value = true
    try {
      const result = await submitSafetyCheck({
        completed: true,
        no_symptoms: noSymptoms,
        symptoms: noSymptoms ? [] : ['uncertain'],
      })
      safetyStatus.value = result.status
      screeningDate.value = result.screening_date ?? null
      await refreshToday()
    } finally {
      submittingCheck.value = false
    }
  }

  async function recheck(): Promise<void> {
    if (safetyStatus.value !== 'clear') return
    safetyStatus.value = 'ask'
    screeningDate.value = null
    try {
      await submitSafetyCheck({ completed: false, no_symptoms: false, symptoms: [] })
      await refreshToday()
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '请求失败，请稍后重试。'
    }
  }

  async function saveSignal(payload: DailySignalPayload): Promise<void> {
    if (submittingSignal.value) return
    submittingSignal.value = true
    try {
      await saveDailySignal(payload)
      await refreshToday()
    } finally {
      submittingSignal.value = false
    }
  }

  async function handleSafetyGateError(error: unknown): Promise<boolean> {
    if (!(error instanceof ApiError) || (error.status !== 423 && error.status !== 409)) return false
    safetyStatus.value = error.status === 423 ? 'stop' : 'ask'
    screeningDate.value = null
    await refreshToday()
    return true
  }

  function expireScreeningForNewDay(): boolean {
    if (!screeningDate.value || screeningDate.value === localDateString()) return false
    screeningDate.value = null
    safetyStatus.value = 'ask'
    void refreshToday()
    return true
  }

  function levelLabel(level: TodayLevel): [string, string] {
    const labels: Record<TodayLevel, [string, string]> = {
      ask: ['等待筛查', '安全筛查尚未完成'],
      stop: ['暂停训练', '已触发安全暂停'],
      insufficient_data: ['信息不足', '缺少今天的主观状态'],
      normal: ['按计划', '依据你主动提供的信息'],
      rest_day: ['计划休息日', '今天无需记录状态'],
      downgrade: ['考虑降负荷', '依据你主动提供的信息'],
    }
    return labels[level] || ['状态未知', '']
  }

  function readinessLabel(value: Readiness): string {
    return ({ good: '状态不错', okay: '一般', poor: '状态较差' })[value]
  }

  return {
    safetyStatus, screeningDate, today, loading, submittingCheck, submittingSignal,
    errorMessage, isRestDay, refreshToday, submitCheck, recheck, saveSignal,
    handleSafetyGateError, expireScreeningForNewDay, levelLabel, readinessLabel,
  }
})
