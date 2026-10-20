import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { deleteBodyProfile, getBodyProfile, saveBodyProfile, saveBodyWeight, saveWeightTarget } from '@/api/profile'
import type { BodyProfile, BodyProfilePayload, WeightHistoryItem } from '@/api/types'

export const useProfileStore = defineStore('profile', () => {
  const profile = ref<BodyProfile | null>(null)
  const weightHistory = ref<WeightHistoryItem[]>([])
  const legacyDemographics = ref<{ age_years: number | null; biological_sex: BodyProfile['biological_sex'] } | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const bmi = computed(() => {
    if (!profile.value || profile.value.age_band === 'under_18') return null
    const heightM = profile.value.height_cm / 100
    return profile.value.weight_kg / (heightM * heightM)
  })

  async function load(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const result = await getBodyProfile()
      profile.value = result.profile
      weightHistory.value = result.weight_history
      legacyDemographics.value = result.legacy_demographics
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '身体档案暂时无法读取。'
      throw cause
    } finally { loading.value = false }
  }

  async function save(payload: BodyProfilePayload): Promise<string> {
    saving.value = true
    try {
      const result = await saveBodyProfile(payload)
      await load()
      return result.message
    } finally { saving.value = false }
  }

  async function remove(): Promise<string> {
    const result = await deleteBodyProfile()
    await load()
    return result.message
  }

  async function recordWeight(weightKg: number): Promise<string> {
    const result = await saveBodyWeight(weightKg)
    await load()
    return result.message
  }

  async function setTarget(targetWeight: number | null): Promise<string> {
    const result = await saveWeightTarget(targetWeight)
    await load()
    return result.message
  }

  return { profile, weightHistory, legacyDemographics, loading, saving, error, bmi, load, save, remove, recordWeight, setTarget }
})
