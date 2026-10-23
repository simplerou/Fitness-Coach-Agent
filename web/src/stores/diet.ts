import { computed, reactive, ref } from 'vue'
import { defineStore } from 'pinia'
import { addWater, createDietPlan, deleteMeal, getDietLog, getDietPlanHistory, getDietProfile, getDietTargets, getFoodDetail, saveDietProfile, saveMeal, searchFoods, updateDietDayReview } from '@/api/diet'
import type { DietFood, DietLogResponse, DietMeal, DietMealPayload, DietMealType, DietPlanData, DietPlanHistoryItem, DietProfile, DietSelectedFood, DietTargetsResponse } from '@/api/types'
import { localDateString } from '@/utils/date'

const blankProfile = (): DietProfile => ({ goal: null, activity_level: null, training_type: null, training_time: null, training_end_time: null, dietary_preference: null, allergies: null, allergies_reviewed: false, avoid_foods: null, medical_conditions: null, injuries: null, health_reviewed: false, cooking_access: null, eating_out_per_week: null, budget_note: null, water_target_ml: null })
const macroKeys = ['calories_kcal', 'protein_g', 'carbs_g', 'fat_g'] as const
type MacroKey = typeof macroKeys[number]
const foodDetailCache = new Map<string, DietFood>()

function numericFoodValue(value: unknown): number | null {
  if (value && typeof value === 'object') {
    const object = value as Record<string, unknown>
    value = object.value ?? object.amount ?? object.content
  }
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value !== 'string') return null
  const match = value.replace(/,/g, '').match(/-?\d+(?:\.\d+)?/)
  return match ? Number(match[0]) : null
}

function normalizeFood(item: DietFood): DietSelectedFood {
  const source = item as Record<string, unknown>
  const nutritionLists = [source.nutrition, source.nutrients, source.nutrition_info, source.nutrition_per_100g].find(Array.isArray) as Array<Record<string, unknown>> | undefined
  const listValues: Record<string, unknown> = {}
  for (const entry of nutritionLists || []) {
    const label = String(entry.name || entry.nutrient || entry.label || entry.title || '').toLowerCase()
    const value = entry.value ?? entry.amount ?? entry.content
    if (/protein|蛋白/.test(label)) listValues.protein_g = value
    else if (/carb|碳水/.test(label)) listValues.carbs_g = value
    else if (/fat|脂肪/.test(label)) listValues.fat_g = value
    else if (/energy|calor|能量|热量/.test(label)) listValues.calories_kcal = value
  }
  const sources = [source, source.nutrition, source.nutrients, source.nutrition_info, source.nutrition_per_100g, listValues].filter((value): value is Record<string, unknown> => Boolean(value) && !Array.isArray(value) && typeof value === 'object')
  const lookup = (aliases: string[]): number | null => {
    for (const candidate of sources) for (const [key, value] of Object.entries(candidate)) {
      if (aliases.includes(key.toLowerCase().replace(/[^a-z0-9]/g, ''))) {
        const number = numericFoodValue(value)
        if (number != null) return number
      }
    }
    return null
  }
  return {
    name: String(source.name || source.food_name || source.title || source.foodName || source.description || '未命名食物'),
    id: String(source.id ?? source.food_id ?? source.code ?? ''), per100: true, grams: 100,
    macros: {
      calories_kcal: lookup(['calorieskcal', 'caloriekcal', 'calorykcal', 'energykcal', 'kcal', 'calories', 'calory', 'calorie', 'energy']),
      protein_g: lookup(['proteing', 'protein', 'protein100g', 'proteinper100g']),
      carbs_g: lookup(['carbsg', 'carbs', 'carbohydrateg', 'carbohydrate', 'carbohydrates', 'carbohydrate100g']),
      fat_g: lookup(['fatg', 'fat', 'fat100g', 'fatper100g']),
    },
  }
}

async function loadFoodSearchDetail(item: DietFood): Promise<DietFood> {
  const row = item as Record<string, unknown>
  const code = row.code || row.food_code || row.food_id || row.id
  if (!code) {
    const macros = normalizeFood(item).macros
    return { ...row, ...macros, __detail_loaded: true,
      __detail_unavailable: macroKeys.some((macro) => macros[macro] == null) }
  }

  try {
    const key = String(code)
    let detail = foodDetailCache.get(key)
    if (!detail) {
      detail = (await getFoodDetail(key)).food
      foodDetailCache.set(key, detail)
    }
    const detailValues = normalizeFood(detail).macros
    const searchValues = normalizeFood(item).macros
    const macros = Object.fromEntries(macroKeys.map((macro) => [
      macro, detailValues[macro] ?? searchValues[macro],
    ])) as Record<MacroKey, number | null>
    return {
      ...row, ...(detail as Record<string, unknown>), ...macros,
      __detail_loaded: true,
      __detail_unavailable: macroKeys.some((macro) => macros[macro] == null),
    }
  } catch {
    const macros = normalizeFood(item).macros
    return { ...row, ...macros, __detail_loaded: true,
      __detail_unavailable: macroKeys.some((macro) => macros[macro] == null) }
  }
}

async function loadFoodSearchDetails(items: DietFood[]): Promise<DietFood[]> {
  const result = [...items]
  let nextIndex = 0
  const worker = async (): Promise<void> => {
    while (nextIndex < items.length) {
      const index = nextIndex++
      result[index] = await loadFoodSearchDetail(items[index])
    }
  }
  await Promise.all(Array.from({ length: Math.min(4, items.length) }, worker))
  return result
}

export const useDietStore = defineStore('diet', () => {
  const selectedDate = ref(localDateString())
  const log = ref<DietLogResponse>({ log_date: selectedDate.value, items: [], water_ml: 0, day_complete: false })
  const profile = reactive<DietProfile>(blankProfile())
  const targets = ref<DietTargetsResponse | null>(null)
  const plan = ref<DietPlanData | null>(null)
  const planHistory = ref<DietPlanHistoryItem[]>([])
  const loading = ref(false)
  const savingProfile = ref(false)
  const generatingPlan = ref(false)
  const searching = ref(false)
  const searchKeyword = ref('')
  const foods = ref<DietFood[]>([])
  const selectedFoods = ref<DietSelectedFood[]>([])
  const mealDialogOpen = ref(false)
  const editingMealId = ref<number | null>(null)
  const mealForm = reactive<DietMealPayload>({ log_date: selectedDate.value, meal_type: 'breakfast', description: '', note: null, portion: null, eaten_at: null, calories_kcal: null, protein_g: null, carbs_g: null, fat_g: null, nutrition_source: null })
  const waterInput = ref<number | null>(null)
  const futureDate = computed(() => selectedDate.value > localDateString())
  const meals = computed(() => futureDate.value ? [] : log.value.items)
  const sums = computed(() => Object.fromEntries(macroKeys.map((key) => {
    const valid = meals.value.filter((meal) => meal[key] != null)
    return [key, { value: valid.reduce((total, meal) => total + Number(meal[key]), 0), count: valid.length }]
  })) as Record<MacroKey, { value: number; count: number }>)
  const selectedTotals = computed(() => {
    const result = { calories_kcal: 0, protein_g: 0, carbs_g: 0, fat_g: 0 }
    const complete = selectedFoods.value.length > 0 && selectedFoods.value.every((food) => food.per100 && macroKeys.every((key) => food.macros[key] != null))
    if (complete) for (const food of selectedFoods.value) for (const key of macroKeys) result[key] += Number(food.macros[key]) * food.grams / 100
    return { complete, values: result }
  })
  const waterTarget = computed(() => targets.value?.hydration?.target_ml ?? null)
  const waterProgress = computed(() => waterTarget.value ? Math.min(100, log.value.water_ml / waterTarget.value * 100) : 0)

  async function loadProfile(): Promise<void> {
    const result = await getDietProfile()
    Object.assign(profile, blankProfile(), result.profile || {})
  }
  async function loadTargets(): Promise<void> { targets.value = await getDietTargets() }
  async function loadLog(): Promise<void> {
    if (futureDate.value) {
      log.value = { log_date: selectedDate.value, items: [], water_ml: 0, day_complete: false }
      return
    }
    log.value = await getDietLog(selectedDate.value)
  }
  async function loadHistory(): Promise<void> {
    const result = await getDietPlanHistory()
    planHistory.value = result.items
    if (result.items.length && !plan.value) plan.value = result.items[0].plan_data
  }
  async function loadAll(): Promise<void> {
    loading.value = true
    try { await Promise.all([loadProfile(), loadTargets(), loadLog(), loadHistory()]) }
    finally { loading.value = false }
  }
  async function saveProfileData(): Promise<string> {
    savingProfile.value = true
    try { const result = await saveDietProfile({ ...profile }); await loadTargets(); return result.message || '饮食规划档案已保存。' }
    finally { savingProfile.value = false }
  }
  async function generatePlan(consent: boolean): Promise<string> {
    if (!consent) throw new Error('请先阅读并勾选 AI 数据使用说明；不授权也可以继续记录饮食。')
    generatingPlan.value = true
    try { plan.value = await createDietPlan(); await loadHistory(); return plan.value.message || '本周饮食计划已更新。' }
    finally { generatingPlan.value = false }
  }
  async function loadSelectedDate(): Promise<void> { await loadLog() }
  async function searchFoodsForKeyword(keyword: string): Promise<void> {
    searchKeyword.value = keyword.trim()
    if (!searchKeyword.value) throw new Error('请先输入食物名称。')
    searching.value = true
    try { foods.value = await loadFoodSearchDetails((await searchFoods(searchKeyword.value)).items) }
    finally { searching.value = false }
  }
  async function addFood(item: DietFood): Promise<void> {
    let selected = item
    const row = item as Record<string, unknown>
    // 薄荷搜索结果有时只返回 id；也要用它查询详情，避免食物被加入但营养值一直为空。
    const code = row.code || row.food_code || row.food_id || row.id
    if (code && !row.__detail_loaded) {
      try { selected = (await getFoodDetail(String(code))).food }
      catch { /* 保留搜索结果，让用户仍可选择食物名称 */ }
    }
    selectedFoods.value.push(normalizeFood(selected))
    syncMealFromFoods()
  }
  function addCustomFood(): void {
    selectedFoods.value.push({ name: searchKeyword.value, id: '', per100: false, grams: 100, macros: { calories_kcal: null, protein_g: null, carbs_g: null, fat_g: null } })
    syncMealFromFoods()
  }
  function updateFoodGrams(index: number, grams: number): void {
    const food = selectedFoods.value[index]
    if (food) { food.grams = Math.max(1, Math.min(3000, Math.round(Number(grams) || 1))); syncMealFromFoods() }
  }
  function removeFood(index: number): void { selectedFoods.value.splice(index, 1); syncMealFromFoods() }
  function syncMealFromFoods(): void {
    mealForm.description = selectedFoods.value.map((food) => food.name).join('、').slice(0, 500)
    mealForm.portion = selectedFoods.value.map((food) => `${food.name} ${food.grams}g`).join('；').slice(0, 120) || null
    if (selectedTotals.value.complete) {
      mealForm.calories_kcal = Math.round(selectedTotals.value.values.calories_kcal * 10) / 10
      mealForm.protein_g = Math.round(selectedTotals.value.values.protein_g * 10) / 10
      mealForm.carbs_g = Math.round(selectedTotals.value.values.carbs_g * 10) / 10
      mealForm.fat_g = Math.round(selectedTotals.value.values.fat_g * 10) / 10
      mealForm.nutrition_source = 'estimate'
    } else if (selectedFoods.value.length) {
      mealForm.calories_kcal = mealForm.protein_g = mealForm.carbs_g = mealForm.fat_g = null
      mealForm.nutrition_source = null
    }
  }
  function openMeal(meal: DietMeal | null = null, mealType?: DietMealType): void {
    if (futureDate.value) throw new Error('计划日期还未到，暂时不能记录餐食。')
    editingMealId.value = meal?.id ?? null
    selectedFoods.value = []
    foods.value = []
    searchKeyword.value = ''
    Object.assign(mealForm, { log_date: selectedDate.value, meal_type: meal?.meal_type ?? mealType ?? (['breakfast', 'lunch', 'dinner'].find((type) => !log.value.items.some((item) => item.meal_type === type)) || 'snack'), description: meal?.description ?? '', note: meal?.note ?? null, portion: meal?.portion ?? null, eaten_at: meal?.eaten_at ?? null, calories_kcal: meal?.calories_kcal ?? null, protein_g: meal?.protein_g ?? null, carbs_g: meal?.carbs_g ?? null, fat_g: meal?.fat_g ?? null, nutrition_source: meal?.nutrition_source ?? null })
    mealDialogOpen.value = true
  }
  function closeMeal(): void { mealDialogOpen.value = false; editingMealId.value = null }
  async function saveMealData(): Promise<string> {
    if (!mealForm.description.trim()) throw new Error('请先搜索并选择至少一种食物。')
    if (macroKeys.some((key) => mealForm[key] != null) && !mealForm.nutrition_source) throw new Error('填写热量或营养数据时，请选择数据来源（标签/可靠测量或自行估算）。')
    const result = await saveMeal({ ...mealForm, log_date: selectedDate.value }, editingMealId.value)
    closeMeal()
    await loadLog()
    return result.message || '餐食记录已保存。'
  }
  async function removeMeal(mealId: number): Promise<string> { const result = await deleteMeal(mealId); await loadLog(); return result.message }
  async function addWaterIntake(): Promise<string> {
    if (futureDate.value) throw new Error('计划日期还未到，暂时不能记录饮水。')
    if (waterInput.value == null) throw new Error('请输入本次饮水量。')
    const result = await addWater(selectedDate.value, waterInput.value)
    waterInput.value = null
    await loadLog()
    return result.message || '饮水记录已累计。'
  }
  async function markDayComplete(value: boolean): Promise<string> {
    if (futureDate.value) throw new Error('计划日期还未到，暂时不能记录饮食。')
    const result = await updateDietDayReview(selectedDate.value, value)
    await loadLog()
    return result.message
  }
  return {
    selectedDate, log, profile, targets, plan, planHistory, loading, savingProfile, generatingPlan, searching, searchKeyword, foods,
    selectedFoods, mealDialogOpen, editingMealId, mealForm, waterInput, futureDate, meals, sums, selectedTotals,
    waterTarget, waterProgress, loadAll, loadProfile, loadTargets, loadLog, loadHistory, saveProfileData, generatePlan,
    loadSelectedDate, searchFoodsForKeyword, addFood, addCustomFood, updateFoodGrams, removeFood, openMeal, closeMeal,
    saveMealData, removeMeal, addWaterIntake, markDayComplete,
  }
})
