<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import BaseDialog from '@/components/common/BaseDialog.vue'
import { useDietStore } from '@/stores/diet'
import { useNotice } from '@/composables/useNotice'
import type { DietMeal, DietMealType } from '@/api/types'

const diet = useDietStore()
const notice = useNotice()
const query = ref('')
const searchStatus = ref('搜索并选择食物，所选食物会显示在这里。')
const mealTypes: Array<{ value: DietMealType; label: string }> = [{ value: 'breakfast', label: '早餐' }, { value: 'lunch', label: '午餐' }, { value: 'dinner', label: '晚餐' }, { value: 'snack', label: '加餐' }]
const dialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const title = computed(() => diet.editingMealId == null ? '记录一餐' : '修改餐食')
const total = computed(() => diet.selectedTotals.values)
watch(() => diet.mealDialogOpen, (open) => open ? dialog.value?.open() : dialog.value?.close())

async function search(): Promise<void> {
  try {
    await diet.searchFoodsForKeyword(query.value)
    searchStatus.value = diet.foods.length ? '请选择食物；点击后会读取详情并按每 100 克换算。' : `没有找到结果，请更换关键词或添加“${diet.searchKeyword}”作为自定义食物。`
  } catch (error) { searchStatus.value = error instanceof Error ? error.message : '食物查询失败。' }
}
async function addFood(index: number): Promise<void> {
  const food = diet.foods[index]
  if (!food) return
  searchStatus.value = '正在读取薄荷食物详情…'
  await diet.addFood(food)
  searchStatus.value = diet.selectedTotals.complete ? '已按薄荷每 100 克数据和所选克数实时换算。' : '自定义食物没有营养数据，暂不能汇总整餐。'
}
async function save(): Promise<void> {
  try { notice.notify(await diet.saveMealData(), 'success') }
  catch (error) { notice.notify(error instanceof Error ? error.message : '餐食记录保存失败。', 'error') }
}
function setMealType(value: string): void { diet.mealForm.meal_type = value as DietMealType }

defineExpose({ open: (meal?: DietMeal | null) => { diet.openMeal(meal || null); query.value = ''; searchStatus.value = '搜索并选择食物，所选食物会显示在这里。' } })
</script>

<template>
  <BaseDialog ref="dialog" class="user-dialog diet-meal-dialog" aria-labelledby="diet-meal-dialog-title" @close="diet.closeMeal">
    <div class="user-dialog-top"><div><p class="eyebrow">MEAL NOTES</p><h2 id="diet-meal-dialog-title">{{ title }}</h2></div><button class="user-dialog-close" type="button" aria-label="关闭餐食记录" @click="diet.closeMeal">×</button></div>
    <p class="diet-meal-dialog-date">记录日期：<b>{{ diet.selectedDate }}</b></p>
    <form class="form-stack" @submit.prevent="save">
      <label class="field"><span>餐别</span><select :value="diet.mealForm.meal_type" required @change="setMealType(($event.target as HTMLSelectElement).value)"><option v-for="type in mealTypes" :key="type.value" :value="type.value">{{ type.label }}</option></select></label>
      <p v-if="diet.editingMealId != null" class="fine-print">当前记录：{{ diet.mealForm.description }}{{ diet.mealForm.portion ? ` · ${diet.mealForm.portion}` : '' }}</p>
      <section class="diet-food-picker" aria-label="搜索并选择食物">
        <label class="field"><span>搜索食物</span><input v-model="query" type="search" maxlength="80" placeholder="例如：米饭、鸡蛋" autocomplete="off" @keydown.enter.prevent="search" /></label>
        <button class="button button-quiet" type="button" :disabled="diet.searching" @click="search">{{ diet.searching ? '正在查询…' : '查询薄荷食物库' }}</button>
        <p class="fine-print" aria-live="polite">{{ searchStatus }}</p>
        <div class="diet-food-search-results" aria-live="polite">
          <button v-for="(food,index) in diet.foods" :key="String(food.code || food.id || index)" class="diet-food-result" type="button" @click="addFood(index)"><strong>{{ String(food.name || food.food_name || food.title || '未命名食物') }}</strong><small>按每 100 克 · {{ food.calories_kcal ?? food.kcal ?? '—' }} kcal · 蛋白质 {{ food.protein_g ?? '—' }}g · 碳水 {{ food.carbs_g ?? '—' }}g · 脂肪 {{ food.fat_g ?? '—' }}g</small></button>
          <button v-if="diet.searchKeyword && diet.foods.length === 0" class="button button-quiet" type="button" @click="diet.addCustomFood">添加“{{ diet.searchKeyword }}”</button>
        </div>
        <div v-if="diet.selectedFoods.length" class="diet-selected-foods">
          <div v-for="(food,index) in diet.selectedFoods" :key="`${food.id}-${index}`" class="diet-selected-food">
            <div><strong>{{ food.name }}</strong><small v-if="food.macros.calories_kcal != null && food.macros.protein_g != null && food.macros.carbs_g != null && food.macros.fat_g != null">本份 {{ food.grams }}g：{{ Math.round(food.macros.calories_kcal * food.grams / 100) }} kcal · 蛋白质 {{ (food.macros.protein_g * food.grams / 100).toFixed(1) }}g · 碳水 {{ (food.macros.carbs_g * food.grams / 100).toFixed(1) }}g · 脂肪 {{ (food.macros.fat_g * food.grams / 100).toFixed(1) }}g</small><small v-else>自定义食物暂无营养数据</small></div>
            <label>克数<input type="number" min="1" max="3000" step="1" :value="food.grams" :aria-label="`${food.name}的克数`" @input="diet.updateFoodGrams(index, Number(($event.target as HTMLInputElement).value))" /></label><button class="text-button diet-delete-button" type="button" :aria-label="`移除${food.name}`" @click="diet.removeFood(index)">移除</button>
          </div>
        </div>
        <div v-if="diet.selectedFoods.length" class="diet-nutrition-summary"><template v-if="diet.selectedTotals.complete"><strong>本餐营养合计</strong><div><span>热量 <b>{{ Math.round(total.calories_kcal) }} kcal</b></span><span>蛋白质 <b>{{ total.protein_g.toFixed(1) }} g</b></span><span>碳水 <b>{{ total.carbs_g.toFixed(1) }} g</b></span><span>脂肪 <b>{{ total.fat_g.toFixed(1) }} g</b></span></div><small>根据所选克数和薄荷每 100 克数据换算，数值为估算值。</small></template><small v-else>本餐营养合计暂不可用；请移除没有营养数据的食物后查看自动汇总。</small></div>
      </section>
      <label class="field"><span>进食时间（选填）</span><input v-model="diet.mealForm.eaten_at" type="time" /></label>
      <label class="field"><span>补充说明（选填）</span><input v-model="diet.mealForm.note" maxlength="240" placeholder="如外食、烹饪方式或用餐感受" /></label>
      <button class="button button-primary" type="submit">{{ diet.editingMealId == null ? '保存餐食' : '保存修改' }}</button>
    </form>
  </BaseDialog>
</template>
