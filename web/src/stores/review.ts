import { ref } from 'vue'
import { defineStore } from 'pinia'
import { getWeeklyReview } from '@/api/review'
import type { WeeklyReviewResponse } from '@/api/types'
import { localDateString, mondayFor, shiftDate } from '@/utils/date'

export const useReviewStore = defineStore('review', () => {
  const selectedDate = ref(localDateString())
  const result = ref<WeeklyReviewResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  async function load(): Promise<void> {
    loading.value = true
    error.value = null
    try { result.value = await getWeeklyReview(selectedDate.value) }
    catch (cause) { error.value = cause instanceof Error ? cause.message : '暂时无法读取训练计划和记录。' }
    finally { loading.value = false }
  }
  function moveWeek(offset: number): void { selectedDate.value = shiftDate(mondayFor(selectedDate.value || localDateString()), 7 * offset); void load() }
  function currentWeek(): void { selectedDate.value = localDateString(); void load() }
  return { selectedDate, result, loading, error, load, moveWeek, currentWeek }
})
