import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { useAuthStore } from './auth'
import { useDietStore } from './diet'
import { useLogStore } from './log'
import { useProfileStore } from './profile'
import { useReviewStore } from './review'
import { useSafetyStore } from './safety'
import { useShapingStore } from './shaping'
import { useShapingIntelligenceStore } from './shapingIntelligence'
import { useTrainingStore } from './training'
import { localDateString } from '@/utils/date'

export type HomeModuleId = 'actions' | 'progress' | 'quick' | 'smart' | 'report'
export interface HomeModulePreference { id: HomeModuleId; collapsed: boolean }

const defaults = (): HomeModulePreference[] => [
  { id: 'actions', collapsed: false },
  { id: 'progress', collapsed: false },
  { id: 'quick', collapsed: false },
  { id: 'smart', collapsed: false },
  { id: 'report', collapsed: false },
]

export const useHomeStore = defineStore('home', () => {
  const auth = useAuthStore()
  const safety = useSafetyStore()
  const profile = useProfileStore()
  const diet = useDietStore()
  const logs = useLogStore()
  const review = useReviewStore()
  const shaping = useShapingStore()
  const intelligence = useShapingIntelligenceStore()
  const training = useTrainingStore()
  const modules = ref<HomeModulePreference[]>(defaults())
  const loading = ref(false)
  const errors = ref<string[]>([])

  const storageKey = computed(() => `fitnessCoachHomeLayout:${auth.user?.id ?? 'guest'}`)
  const today = computed(() => localDateString())
  const todayLog = computed(() => logs.items.find(item => item.training_date === today.value) ?? null)
  const latestMeasurement = computed(() => shaping.measurements.at(-1) ?? null)
  const latestReport = computed(() => intelligence.reports.find(item => item.period_type === 'week') ?? intelligence.reports[0] ?? null)

  function restorePreferences(): void {
    modules.value = defaults()
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey.value) || 'null') as HomeModulePreference[] | null
      if (!Array.isArray(saved)) return
      const valid = saved.filter(row => defaults().some(item => item.id === row.id))
      const missing = defaults().filter(row => !valid.some(item => item.id === row.id))
      modules.value = [...valid, ...missing].map(row => ({ id: row.id, collapsed: Boolean(row.collapsed) }))
    } catch { /* 浏览器禁用存储时仍使用默认布局。 */ }
  }

  function persist(): void {
    try { localStorage.setItem(storageKey.value, JSON.stringify(modules.value)) }
    catch { /* 布局继续在当前标签页生效。 */ }
  }

  function toggle(id: HomeModuleId): void {
    const item = modules.value.find(row => row.id === id)
    if (item) { item.collapsed = !item.collapsed; persist() }
  }

  function move(id: HomeModuleId, offset: -1 | 1): void {
    const index = modules.value.findIndex(row => row.id === id)
    const target = index + offset
    if (index < 0 || target < 0 || target >= modules.value.length) return
    const next = [...modules.value]
    ;[next[index], next[target]] = [next[target], next[index]]
    modules.value = next
    persist()
  }

  function reorder(source: HomeModuleId, target: HomeModuleId): void {
    if (source === target) return
    const next = [...modules.value]
    const from = next.findIndex(row => row.id === source)
    const to = next.findIndex(row => row.id === target)
    if (from < 0 || to < 0) return
    const [item] = next.splice(from, 1)
    next.splice(to, 0, item)
    modules.value = next
    persist()
  }

  async function load(): Promise<void> {
    loading.value = true
    errors.value = []
    review.selectedDate = today.value
    const tasks = [
      safety.refreshToday(), profile.load(), diet.loadAll(), logs.load(), review.load(),
      shaping.load(), training.load(), intelligence.loadDietAdjustment(today.value), intelligence.loadReports(), intelligence.analyze(),
    ]
    const results = await Promise.allSettled(tasks)
    errors.value = results.flatMap(result => result.status === 'rejected'
      ? [result.reason instanceof Error ? result.reason.message : '部分首页数据暂时无法读取。'] : [])
    loading.value = false
  }

  watch(() => auth.user?.id, restorePreferences, { immediate: true })

  return {
    modules, loading, errors, todayLog, latestMeasurement, latestReport,
    restorePreferences, toggle, move, reorder, load,
  }
})
