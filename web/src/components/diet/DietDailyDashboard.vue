<script setup lang="ts">
import { computed, ref } from 'vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import DietMealDialog from './DietMealDialog.vue'
import DietTrainingAdjustment from './DietTrainingAdjustment.vue'
import RingProgress from '@/components/charts/RingProgress.vue'
import { useDietStore } from '@/stores/diet'
import { useShapingIntelligenceStore } from '@/stores/shapingIntelligence'
import { useNotice } from '@/composables/useNotice'
import type { DietMeal, DietMealType } from '@/api/types'

const diet = useDietStore()
const intelligence = useShapingIntelligenceStore()
const notice = useNotice()
const mealDialog = ref<InstanceType<typeof DietMealDialog> | null>(null)
const deleteConfirm = ref(false)
const selectedDelete = ref<DietMeal | null>(null)
const groups: Array<{ type: DietMealType; label: string }> = [
  { type: 'breakfast', label: '早餐' }, { type: 'lunch', label: '午餐' }, { type: 'dinner', label: '晚餐' }, { type: 'snack', label: '加餐' },
]
const target = computed(() => intelligence.dietAdjustment?.date === diet.selectedDate && intelligence.dietAdjustment.status === 'adopted' && intelligence.dietAdjustment.suggestion
  ? intelligence.dietAdjustment.suggestion : diet.targets?.target ?? null)
const calories = computed(() => diet.sums.calories_kcal.value)
const targetBasis = computed(() => {
  const value = target.value
  if (!value) return '完善档案后显示目标计算依据'
  return 'basis' in value ? value.basis : value.reason
})
const macroRows = computed(() => [
  { key: 'protein_g' as const, label: '蛋白质', value: diet.sums.protein_g.value, target: target.value?.protein_g ?? 0 },
  { key: 'carbs_g' as const, label: '碳水', value: diet.sums.carbs_g.value, target: target.value?.carbs_g ?? 0 },
  { key: 'fat_g' as const, label: '脂肪', value: diet.sums.fat_g.value, target: target.value?.fat_g ?? 0 },
])
function mealsFor(type: DietMealType) { return diet.meals.filter((item) => item.meal_type === type) }
function mealCalories(type: DietMealType) { return mealsFor(type).reduce((sum, item) => sum + Number(item.calories_kcal ?? 0), 0) }
function openMeal(meal: DietMeal | null = null, type?: DietMealType) {
  try { mealDialog.value?.open(meal, type) }
  catch (error) { notice.notify(error instanceof Error ? error.message : '暂时不能记录餐食。', 'info') }
}
function askDelete(meal: DietMeal) { selectedDelete.value = meal; deleteConfirm.value = true }
async function removeMeal() {
  if (!selectedDelete.value) return
  try { notice.notify(await diet.removeMeal(selectedDelete.value.id), 'success') } catch (error) { notice.notify(error instanceof Error ? error.message : '餐食记录删除失败。', 'error') }
  finally { deleteConfirm.value = false; selectedDelete.value = null }
}
async function addWater(amount: number) {
  diet.waterInput = amount
  try { notice.notify(await diet.addWaterIntake(), 'success') } catch (error) { notice.notify(error instanceof Error ? error.message : '饮水记录失败。', 'error') }
}
async function toggleComplete() {
  try { notice.notify(await diet.markDayComplete(!diet.log.day_complete), 'success') } catch (error) { notice.notify(error instanceof Error ? error.message : '当天完整度更新失败。', 'error') }
}
</script>

<template>
  <div class="diet-workspace-grid">
    <section class="diet-meal-column">
      <article v-for="group in groups" :key="group.type" class="meal-block content-card">
        <header><div><h3>{{ group.label }}</h3><span>{{ Math.round(mealCalories(group.type)) }} kcal</span></div><button class="text-button" :disabled="diet.futureDate" @click="openMeal(null, group.type)">+ 添加</button></header>
        <div v-if="!mealsFor(group.type).length" class="meal-empty">还没有{{ group.label }}记录</div>
        <article v-for="meal in mealsFor(group.type)" :key="meal.id" class="meal-row">
          <div><b>{{ meal.description }}</b><small>{{ meal.portion || '份量未记录' }}</small><span>{{ meal.calories_kcal == null ? '热量未记录' : `${meal.calories_kcal} kcal` }} · 蛋白 {{ meal.protein_g ?? '未记录' }} g</span></div>
          <div><button class="text-button" @click="openMeal(meal)">改</button><button class="text-button danger-text" @click="askDelete(meal)">删</button></div>
        </article>
        <i class="meal-share"><span :style="{ width: `${target?.calories_kcal ? Math.min(100, mealCalories(group.type) / target.calories_kcal * 100) : 0}%` }" /></i>
      </article>
    </section>

    <section class="nutrition-dashboard content-card">
      <header><div><h2>当日营养</h2><p>{{ targetBasis }}</p></div><span>{{ diet.selectedDate }}</span></header>
      <div class="nutrition-ring"><RingProgress :value="calories" :max="target?.calories_kcal ?? 0" :tone="target && calories > target.calories_kcal ? 'danger' : 'brand'" unit="kcal" label="摄入" :size="142" /><div><strong>{{ Math.round(calories) }} / {{ target?.calories_kcal ?? '未设置' }}</strong><span>已记录 / 今日目标</span></div></div>
      <div class="nutrition-bars"><div v-for="row in macroRows" :key="row.key"><p><span>{{ row.label }}</span><b>{{ row.value.toFixed(1) }} / {{ row.target || '未设置' }} g</b></p><i><span :class="{ over: row.target && row.value > row.target }" :style="{ width: `${row.target ? Math.min(100, row.value / row.target * 100) : 0}%` }" /></i></div></div>
      <div class="water-dashboard"><div><h3>饮水</h3><p>{{ diet.log.water_ml }} / {{ diet.waterTarget ?? '未设置' }} ml</p></div><div class="water-drops"><i v-for="index in 8" :key="index" :class="{ filled: index <= Math.ceil(diet.waterProgress / 12.5) }" /></div><div class="water-actions"><button class="button button-quiet" @click="addWater(250)">+250 ml</button><button class="button button-quiet" @click="addWater(500)">+500 ml</button></div></div>
      <button class="button" :class="diet.log.day_complete ? 'button-quiet' : 'button-primary'" :disabled="diet.futureDate" @click="toggleComplete">{{ diet.log.day_complete ? '已标记当日完成' : '标记当日完成' }}</button>
    </section>

    <DietTrainingAdjustment />
  </div>
  <DietMealDialog ref="mealDialog" />
  <ConfirmDialog v-model:open="deleteConfirm" title="删除这条餐食记录？" description="删除后无法恢复；当天完整度标记会被重置。" confirm-text="确认删除" danger @confirm="removeMeal" />
</template>
