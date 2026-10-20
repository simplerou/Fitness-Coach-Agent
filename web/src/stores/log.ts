import { ref } from 'vue'
import { defineStore } from 'pinia'
import { createLog, getLogs, getPlanSession } from '@/api/log'
import type { LogsResponse, PlanSessionDateResponse, TrainingLogPayload, TrainingLogItem } from '@/api/types'
import { useSafetyStore } from '@/stores/safety'
import { localDateString } from '@/utils/date'

export const useLogStore = defineStore('log', () => {
  const safety = useSafetyStore()
  const items = ref<TrainingLogItem[]>([])
  const selectedDate = ref(localDateString())
  const sessionContext = ref<PlanSessionDateResponse | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  async function load(): Promise<void> {
    loading.value = true
    try { items.value = (await getLogs()).items }
    catch (cause) { error.value = cause instanceof Error ? cause.message : '暂时无法读取训练记录。'; if (await safety.handleSafetyGateError(cause)) return; throw cause }
    finally { loading.value = false }
  }
  async function loadContext(): Promise<void> {
    if (!selectedDate.value) return
    try { sessionContext.value = await getPlanSession(selectedDate.value) }
    catch (cause) { sessionContext.value = null; error.value = cause instanceof Error ? cause.message : '暂时无法读取这一天的计划安排。' }
  }
  async function save(payload: TrainingLogPayload): Promise<string> {
    saving.value = true
    try {
      const result = await createLog(payload)
      await load()
      return result.message || '训练记录已保存。'
    } catch (cause) {
      if (await safety.handleSafetyGateError(cause)) throw new Error('请先确认今天的身体状态，再记录今天的训练状态。')
      throw cause
    } finally { saving.value = false }
  }
  return { items, selectedDate, sessionContext, loading, saving, error, load, loadContext, save }
})
