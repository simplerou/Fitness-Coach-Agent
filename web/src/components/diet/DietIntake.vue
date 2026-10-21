<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDietStore } from '@/stores/diet'
import { useShapingIntelligenceStore } from '@/stores/shapingIntelligence'
import { useNotice } from '@/composables/useNotice'
import type { DietMeal } from '@/api/types'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import DietMealDialog from '@/components/diet/DietMealDialog.vue'

const diet = useDietStore()
const intelligence = useShapingIntelligenceStore()
const notice = useNotice()
const router = useRouter()
const mealDialog = ref<InstanceType<typeof DietMealDialog> | null>(null)
const deleteConfirm = ref(false)
const selectedDelete = ref<DietMeal | null>(null)
const mealLabels = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '加餐' }
const intakeTitle = computed(() => diet.meals.length ? `已记录 ${diet.meals.length} 餐，继续补充所选日期饮食` : '记录所选日期的饮食，回顾营养结构')
const intakeCopy = computed(() => diet.meals.length ? '统计仅包含已填写的营养数据。' : '未填写的营养值不会按零推断。')
const intakeAction = computed(() => diet.meals.length ? '继续添加餐食' : '记录第一餐')
const calories = computed(() => diet.sums.calories_kcal)
const macroItems = computed(() => [
  { key: 'carbs_g' as const, title: '碳水', label: 'diet-carbs', color: '#f08a62' },
  { key: 'protein_g' as const, title: '蛋白质', label: 'diet-protein', color: '#27bf8a' },
  { key: 'fat_g' as const, title: '脂肪', label: 'diet-fat', color: '#6188fa' },
])
const effectiveTarget = computed(() => {
  const adjusted = intelligence.dietAdjustment
  if (adjusted?.date === diet.selectedDate && adjusted.status === 'adopted' && adjusted.suggestion) return adjusted.suggestion
  return diet.targets?.status === 'ready' ? diet.targets.target ?? null : null
})
const calorieTarget = computed(() => effectiveTarget.value?.calories_kcal ?? null)
const calorieProgress = computed(() => calorieTarget.value ? Math.min(100, calories.value.value / calorieTarget.value * 100) : 0)
const calorieStyle = computed(() => ({ '--diet-progress': `${calorieProgress.value}%` }))
const waterStatus = computed(() => diet.waterTarget ? '个人参考目标' : '尚未设置饮水参考目标')
const macroChartStyle = computed(() => {
  const carbs = diet.sums.carbs_g; const protein = diet.sums.protein_g; const fat = diet.sums.fat_g
  if (![carbs, protein, fat].every((item) => item.count > 0)) return { '--macro-chart': '#edf0ee' }
  const total = carbs.value * 4 + protein.value * 4 + fat.value * 9
  if (!total) return { '--macro-chart': '#edf0ee' }
  const first = carbs.value * 4 / total * 100; const second = first + protein.value * 4 / total * 100
  return { '--macro-chart': `conic-gradient(#f08a62 0 ${first}%,#27bf8a ${first}% ${second}%,#6188fa ${second}% 100%)` }
})

function openMeal(meal: DietMeal | null = null): void {
  try { mealDialog.value?.open(meal) }
  catch (error) { notice.notify(error instanceof Error ? error.message : '暂时不能记录餐食。', 'info') }
}
function askDelete(meal: DietMeal): void { selectedDelete.value = meal; deleteConfirm.value = true }
async function removeMeal(): Promise<void> {
  if (!selectedDelete.value) return
  try { notice.notify(await diet.removeMeal(selectedDelete.value.id), 'success') }
  catch (error) { notice.notify(error instanceof Error ? error.message : '餐食记录删除失败。', 'error') }
  finally { deleteConfirm.value = false; selectedDelete.value = null }
}
async function addWater(): Promise<void> {
  try { notice.notify(await diet.addWaterIntake(), 'success') }
  catch (error) { notice.notify(error instanceof Error ? error.message : '饮水记录失败。', 'error') }
}
async function toggleComplete(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  try { notice.notify(await diet.markDayComplete(input.checked), 'success') }
  catch (error) { input.checked = !input.checked; notice.notify(error instanceof Error ? error.message : '当天完整度更新失败。', 'error') }
}
function barWidth(key: 'carbs_g' | 'protein_g' | 'fat_g'): string {
  const amount = diet.sums[key]
  const goal = effectiveTarget.value?.[key] || 0
  return amount.count && goal ? `${Math.min(100, amount.value / goal * 100)}%` : '0%'
}
function macroStatus(key: 'carbs_g' | 'protein_g' | 'fat_g'): string {
  const amount = diet.sums[key]
  const goal = effectiveTarget.value?.[key] || 0
  return amount.count ? goal ? amount.value >= goal ? '已达目标' : `还差 ${(goal - amount.value).toFixed(1)}g` : `已记录 ${amount.value.toFixed(1)}g` : '未记录'
}
</script>

<template>
  <div class="diet-intro panel"><p>先完善身体和饮食档案并生成初始计划，再按日记录实际餐食与饮水；系统会对照计划和实际摄入，帮助你逐步调整。数据不足或存在特殊健康情况时，会说明原因，不会猜测缺失数据。</p><label class="field"><span>查看日期</span><input v-model="diet.selectedDate" type="date" required @change="diet.loadSelectedDate" /></label></div>
  <div class="diet-flow-heading"><p class="eyebrow">STEP 02 · DAILY INTAKE</p><h3>记录每日摄入</h3><p>按所选日期记录实际餐食与饮水；没有记录的数据不会按零计算。</p></div>
  <div class="diet-dashboard">
    <article class="panel diet-today-summary"><div class="diet-card-heading"><span class="diet-heading-icon">◉</span><h3>当日饮食摄入</h3><span class="diet-date-note">根据已记录内容</span></div>
      <div class="diet-energy-layout"><div class="diet-calorie-gauge" :style="calorieStyle"><svg viewBox="0 0 200 112" aria-hidden="true"><path class="diet-gauge-track" d="M 14 100 A 86 86 0 0 1 186 100" pathLength="100"/><path class="diet-gauge-value" d="M 14 100 A 86 86 0 0 1 186 100" pathLength="100" :stroke-dasharray="`${calorieProgress} 100`"/></svg><div><span>已记录摄入</span><strong>{{ diet.futureDate || !calories.count ? '—' : Math.round(calories.value) }}</strong><small>千卡</small></div></div><div v-if="calorieTarget" class="diet-target-calorie"><span>个人目标</span><b>{{ calorieTarget }}</b><small>剩余目标 {{ Math.max(0, calorieTarget - calories.value).toFixed(0) }} kcal</small></div></div>
      <div class="diet-intake-status"><span>碳水 <b>{{ macroStatus('carbs_g') }}</b></span><i></i><span>蛋白质 <b>{{ macroStatus('protein_g') }}</b></span><i></i><span>脂肪 <b>{{ macroStatus('fat_g') }}</b></span></div>
    </article>
    <article class="panel diet-insight-card"><p class="eyebrow">DAILY INSIGHT</p><div class="diet-insight-content"><div class="diet-insight-meal"><h3>{{ intakeTitle }}</h3><p>{{ intakeCopy }}</p><button class="button button-primary" type="button" @click="openMeal()">{{ intakeAction }}</button></div>
          <div class="diet-water-quick"><div class="diet-water-quick-total"><span>饮水累计</span><strong>{{ diet.futureDate ? '—' : diet.log.water_ml }} <small>毫升</small></strong></div><div class="diet-water-target-line"><span>{{ waterStatus }}</span><span>{{ diet.waterTarget ? `${diet.waterTarget} 毫升/日` : '仅记录' }}</span></div><div class="diet-progress-track diet-water-progress"><i :style="{ width: `${diet.waterProgress}%` }"></i></div><form class="diet-water-quick-form" @submit.prevent="addWater"><label class="field"><span>本次饮水（毫升）</span><input v-model.number="diet.waterInput" type="number" min="50" max="3000" step="50" required placeholder="例如 250" /></label><button class="button button-primary" type="submit" :disabled="diet.futureDate">记录饮水</button></form><p>仅统计你主动记录的饮水量。</p></div>
    </div></article>
  </div>
  <article class="panel diet-meals-panel"><div class="panel-head"><div><p class="eyebrow">TODAY'S MEALS</p><h3>当天餐食</h3></div><button class="text-button" type="button" :disabled="diet.loading" @click="diet.loadLog">刷新</button></div>
    <label class="diet-complete-row"><input type="checkbox" :checked="diet.log.day_complete" :disabled="diet.futureDate" @change="toggleComplete" /><span>我已记录完这一天吃过的餐食（用于判断数据是否完整）</span></label>
    <div v-if="diet.futureDate" class="empty-state"><p>这是未来的计划日期，暂时还没有实际摄入记录。</p></div><div v-else-if="!diet.meals.length" class="empty-state" aria-live="polite"><p>这一天还没有餐食记录。</p></div>
    <div v-else class="diet-meal-list"><article v-for="meal in diet.meals" :key="meal.id" class="diet-meal-item"><div><span class="tag">{{ mealLabels[meal.meal_type] }}{{ meal.eaten_at ? ` · ${meal.eaten_at}` : '' }}</span><h4>{{ meal.description }}</h4><p v-if="meal.portion">分量：{{ meal.portion }}</p><p>{{ [meal.calories_kcal != null ? `${meal.calories_kcal} kcal` : '', meal.protein_g != null ? `蛋白质 ${meal.protein_g}g` : '', meal.carbs_g != null ? `碳水 ${meal.carbs_g}g` : '', meal.fat_g != null ? `脂肪 ${meal.fat_g}g` : ''].filter(Boolean).join(' · ') || '未填写营养值' }}</p><p v-if="meal.note">{{ meal.note }}</p></div><div class="diet-meal-actions"><button class="text-button" type="button" :disabled="diet.futureDate" @click="openMeal(meal)">编辑</button><button class="text-button diet-delete-button" type="button" :disabled="diet.futureDate" @click="askDelete(meal)">删除</button></div></article></div>
  </article>
  <div class="diet-flow-heading"><p class="eyebrow">STEP 03 · REVIEW</p><h3>对照目标，回顾营养与饮水</h3><p>查看餐食营养目标和个人饮水参考值的记录情况；积累一段时间的数据后，可回到上方重新生成调整建议。</p></div>
  <article class="panel diet-nutrition-card"><div class="diet-card-heading"><span class="diet-heading-icon">◒</span><h3>营养成分</h3><span class="diet-date-note">已填写营养值</span></div>
    <div v-if="diet.targets?.status !== 'ready'" class="diet-target-notice" role="status" aria-live="polite"><span>{{ diet.targets?.message || '正在读取个性化目标…' }} {{ diet.targets?.missing?.length ? `还需补充：${diet.targets.missing.join('、')}。` : '' }}</span><button class="text-button" type="button" @click="router.push({ name: 'profile' })">去补充档案</button></div><p v-else class="diet-target-basis">{{ intelligence.dietAdjustment?.date === diet.selectedDate && intelligence.dietAdjustment.status === 'adopted' ? '当前显示已采纳的当天训练联动目标。' : '当前显示基础每日目标。' }} 能量参考目标：{{ effectiveTarget?.calories_kcal }} kcal。依据：{{ diet.targets.summary?.goal }}；BMR {{ diet.targets.summary?.bmr_kcal }} kcal（{{ diet.targets.summary?.bmr_source }}），TDEE {{ diet.targets.summary?.tdee_kcal }} kcal（{{ diet.targets.summary?.tdee_source }}）。这是估算起点，实际需要会因个体差异而变化。</p>
    <div class="diet-macro-layout"><div class="diet-macro-list"><div v-for="macro in macroItems" :key="macro.key" class="diet-macro-row"><div><span>{{ macro.title }}</span><strong><b>{{ diet.futureDate || !diet.sums[macro.key].count ? '未记录' : diet.sums[macro.key].value.toFixed(1) }}</b><small>{{ effectiveTarget ? `/ ${effectiveTarget[macro.key].toFixed(1)} g` : '/ 完善档案后显示' }}</small></strong></div><div class="diet-progress-track"><i :style="{ width: barWidth(macro.key) }"></i></div><small>{{ macroStatus(macro.key) }}</small></div></div><div class="diet-macro-chart" :style="macroChartStyle" aria-label="已记录三大营养素构成"><span>{{ [diet.sums.carbs_g.count, diet.sums.protein_g.count, diet.sums.fat_g.count].every(Boolean) ? '克数换算' : diet.meals.length ? '数据未齐' : '暂无数据' }}</span></div></div>
    <p class="diet-data-note">仅统计已填写值；碳水 {{ diet.sums.carbs_g.count }}/{{ diet.meals.length }} 餐、蛋白质 {{ diet.sums.protein_g.count }}/{{ diet.meals.length }} 餐、脂肪 {{ diet.sums.fat_g.count }}/{{ diet.meals.length }} 餐有数据。</p>
    <div class="diet-hydration-review"><div><span class="eyebrow">HYDRATION REVIEW</span><strong>{{ diet.futureDate || !diet.log.water_ml ? '尚无饮水记录' : `${diet.log.water_ml} 毫升` }}</strong></div><p>{{ diet.targets?.hydration?.note || '饮水记录和营养摄入使用同一日期；未记录不代表没有饮水。' }}</p></div>
  </article>
  <DietMealDialog ref="mealDialog" />
  <ConfirmDialog v-model:open="deleteConfirm" title="删除这条餐食记录？" description="删除后无法恢复；当天完整度标记会被重置。" confirm-text="确认删除" danger @confirm="removeMeal" />
</template>
