import { computed, reactive, ref } from 'vue'
import { defineStore } from 'pinia'
import { generatePlan, getCurrentPlan, getPlanHistory, getPlanPreferences } from '@/api/plan'
import type { PlanHistoryItem, PlanPreferences, WeekPlan } from '@/api/types'
import { useProfileStore } from '@/stores/profile'
import { localDateString } from '@/utils/date'

export const usePlanStore = defineStore('plan', () => {
  const profileStore = useProfileStore()
  const preferences = reactive<PlanPreferences>({
    goal: 'fitness', days_per_week: 3, training_weekdays: [1, 3, 5],
    experience_level: 'beginner', equipment: ['bodyweight_only'], session_minutes: 30,
    preferred_exercise_ids: [],
  })
  const preferencesLoaded = ref(false)
  const edited = ref(false)
  const loading = ref(false)
  const generating = ref(false)
  const currentPlan = ref<WeekPlan | null>(null)
  const savedAt = ref<string | null>(null)
  const currentWeekStart = ref<string | null>(null)
  const history = ref<PlanHistoryItem[]>([])
  const historyCursor = ref<string | null>(null)
  const historyLoading = ref(false)
  const selectedWeek = ref<string | null>(null)
  const historyPlan = computed(() => history.value.find((item) => item.week_start === selectedWeek.value) ?? null)
  const selectedPlan = computed(() => historyPlan.value?.week_plan ?? currentPlan.value)
  const selectedIsHistorical = computed(() => Boolean(historyPlan.value && historyPlan.value.week_start !== currentWeekStart.value))

  async function loadPreferences(): Promise<void> {
    if (preferencesLoaded.value) return
    const result = await getPlanPreferences()
    if (!edited.value) Object.assign(preferences, result.preferences)
    preferencesLoaded.value = true
  }

  function recommendation(): { goal: PlanPreferences['goal']; reason: string; context: string } {
    const profile = profileStore.profile
    if (!profile) return { goal: preferences.goal, reason: '填写年龄、身高和体重后，我会结合你的档案展示训练方向。', context: '' }
    const target = profile.target_weight_kg
    const current = Number(profile.weight_kg)
    const minor = profile.age_band === 'under_18'
    const bmi = minor ? null : current / ((Number(profile.height_cm) / 100) ** 2)
    let goal: PlanPreferences['goal'] = preferences.goal || 'fitness'
    let reason: string
    if (minor) {
      goal = 'fitness'
      reason = '未满 18 岁时，不根据体重目标或成人 BMI 推荐减重方向。建议以均衡体能和循序渐进的熟悉活动为起点。'
    } else if (target != null && target < current - 0.2) {
      goal = 'fat_loss'
      reason = '你设置的体重目标低于当前记录。可以从提升日常活动开始，逐步建立稳定习惯；计划不会推算减重速度。'
    } else if (target != null && target > current + 0.2) {
      reason = '你设置了高于当前记录的体重目标。训练方向仍由你选择，系统不会仅根据体重推断增重或饮食方案。'
    } else if (target != null) {
      goal = 'fitness'
      reason = '当前记录接近你自设的体重目标。综合体能可作为均衡起点，你也可以选择其他方向。'
    } else if (currentPlan.value?.goal) {
      goal = currentPlan.value.goal
      reason = '你还没有设置体重目标。这里先沿用你本周选择的方向，也可以根据当前身体档案重新选择。'
    } else {
      reason = '你还没有设置体重目标。综合体能是一个均衡起点；身高、体重和 BMI 用于查看与回顾，不单独决定训练方向。'
    }
    const details = `档案：身高 ${profile.height_cm} cm · 当前体重 ${current.toFixed(1)} kg　｜　${bmi == null ? '未成年人不使用成人 BMI 参考值' : `成人 BMI 参考值 ${bmi.toFixed(1)}`}${!minor && target != null ? `　｜　自设目标 ${target.toFixed(1)} kg` : ''}`
    return { goal, reason, context: `${details}。${reason}` }
  }

  async function loadCurrent(): Promise<void> {
    loading.value = true
    try {
      const result = await getCurrentPlan()
      currentWeekStart.value = result.week_start
      currentPlan.value = result.week_plan as WeekPlan | null
      savedAt.value = result.saved_at
      if (!selectedWeek.value || selectedWeek.value === currentWeekStart.value) selectedWeek.value = currentWeekStart.value
    } finally { loading.value = false }
  }

  async function loadHistory(reset = true): Promise<void> {
    if (historyLoading.value) return
    historyLoading.value = true
    try {
      const result = await getPlanHistory(20, reset ? null : historyCursor.value)
      currentWeekStart.value = result.current_week_start
      if (reset) history.value = result.items
      else {
        const known = new Set(history.value.map((item) => item.week_start))
        history.value = history.value.concat(result.items.filter((item) => !known.has(item.week_start)))
      }
      historyCursor.value = result.next_before_week_start
    } finally { historyLoading.value = false }
  }

  async function loadAll(): Promise<void> {
    await Promise.all([profileStore.load().catch(() => undefined), loadPreferences(), loadCurrent(), loadHistory()])
  }

  async function create(): Promise<string> {
    if (!preferences.training_weekdays.length) throw new Error('请至少选择一个训练星期。')
    if (!preferences.equipment.length) throw new Error('请至少选择一种可用器械。')
    if (preferences.equipment.includes('bodyweight_only') && preferences.equipment.length > 1) throw new Error('“仅自重”不能与其他器械同时选择。')
    generating.value = true
    try {
      const result = await generatePlan({ ...preferences, days_per_week: preferences.training_weekdays.length })
      currentPlan.value = result.week_plan
      currentWeekStart.value = result.week_start
      selectedWeek.value = result.week_start
      savedAt.value = result.saved_at
      await loadHistory()
      return result.message || '本周计划已保存。'
    } finally { generating.value = false }
  }

  const selectedWeekday = computed(() => {
    const date = localDateString().split('-').map(Number)
    return new Date(date[0], date[1] - 1, date[2]).getDay() || 7
  })

  return {
    preferences, preferencesLoaded, edited, loading, generating, currentPlan, savedAt, currentWeekStart,
    history, historyCursor, historyLoading, selectedWeek, selectedPlan, selectedIsHistorical,
    selectedWeekday, recommendation, loadPreferences, loadCurrent, loadHistory, loadAll, create,
  }
})
