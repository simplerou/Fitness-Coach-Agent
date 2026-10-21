import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getToday, saveDailySignal } from '@/api/today'
import type { DailySignalPayload, Readiness, TodayLevel, TodayResponse } from '@/api/types'

export const useSafetyStore = defineStore('safety', () => {
  const today = ref<TodayResponse | null>(null)
  const loading = ref(false)
  const submittingSignal = ref(false)
  const errorMessage = ref<string | null>(null)
  const isRestDay = computed(() => today.value?.level === 'rest_day')

  async function refreshToday(): Promise<void> {
    loading.value = true
    errorMessage.value = null
    try {
      today.value = await getToday()
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '请求失败，请稍后重试。'
    } finally {
      loading.value = false
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

  function levelLabel(level: TodayLevel): [string, string] {
    const labels: Record<TodayLevel, [string, string]> = {
      ask: ['信息不足', '今日状态尚未记录'],
      stop: ['暂停训练', '请留意身体状态'],
      insufficient_data: ['信息不足', '缺少今天的主观状态'],
      normal: ['按计划', '依据你主动提供的信息'],
      rest_day: ['计划休息日', '今天无需记录状态'],
      downgrade: ['考虑降低负荷', '依据你主动提供的信息'],
    }
    return labels[level] || ['状态未知', '']
  }

  function readinessLabel(value: Readiness): string {
    return ({ good: '状态不错', okay: '一般', poor: '状态较差' })[value]
  }

  return { today, loading, submittingSignal, errorMessage, isRestDay, refreshToday, saveSignal, levelLabel, readinessLabel }
})
