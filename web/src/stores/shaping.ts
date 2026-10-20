import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { useAuthStore } from './auth'
import * as api from '@/api/shaping'
import { localDateString } from '@/utils/date'
import type { ShapeDashboard, ShapeMeasurementPayload, ShapeMetric, ShapeMutationResult, ShapePhotoView, ShapeTargetMetric } from '@/api/types'

export const useShapingStore = defineStore('shaping', () => {
  const auth = useAuthStore()
  const data = ref<ShapeDashboard | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const error = ref('')
  const today = ref(localDateString())
  let generation = 0
  watch(() => auth.user?.id, () => { generation++; data.value = null; error.value = ''; loading.value = false; saving.value = false })
  const measurements = computed(() => data.value?.measurements ?? [])
  const photos = computed(() => data.value?.photos ?? [])
  const reminders = computed(() => (data.value?.reminders ?? []).map(row => ({ ...row, due: row.next_due_on != null && row.next_due_on <= today.value })))
  function refreshReminderDate(): void { today.value = localDateString() }
  function latest(metric: ShapeMetric) {
    return [...measurements.value].reverse().find(row => row[metric] != null) ?? null
  }
  async function load(): Promise<void> {
    refreshReminderDate()
    const version = ++generation
    loading.value = true
    error.value = ''
    try {
      const result = await api.getShaping()
      if (version === generation) data.value = result
    } catch (cause) {
      if (version === generation) error.value = cause instanceof Error ? cause.message : '塑型数据暂时无法读取。'
      throw cause
    } finally { if (version === generation) loading.value = false }
  }
  async function mutate(operation: () => Promise<ShapeMutationResult>): Promise<string> {
    if (saving.value) throw new Error('正在保存，请稍候。')
    const userId = auth.user?.id
    saving.value = true
    try {
      const result = await operation()
      if (auth.user?.id !== userId) return ''
      await load()
      return [result.message, ...(result.milestone_messages ?? [])].join('\n')
    } finally { if (auth.user?.id === userId) saving.value = false }
  }
  const saveMeasurement = (payload: ShapeMeasurementPayload) => mutate(() => api.saveShapeMeasurement(payload))
  const removeMeasurement = (date: string) => mutate(() => api.deleteShapeMeasurement(date))
  const saveTarget = (metric: ShapeTargetMetric, value: number) => mutate(() => api.saveShapeTarget(metric, value))
  const removeTarget = (metric: ShapeTargetMetric) => mutate(() => api.deleteShapeTarget(metric))
  const savePhoto = (date: string, view: ShapePhotoView, image: string) => mutate(() => api.saveShapePhoto(date, view, image))
  const removePhoto = (id: number) => mutate(() => api.deleteShapePhoto(id))
  return { data, measurements, photos, reminders, loading, saving, error, latest, load, refreshReminderDate, saveMeasurement, removeMeasurement, saveTarget, removeTarget, savePhoto, removePhoto }
})
