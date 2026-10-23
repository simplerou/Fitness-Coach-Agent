<script setup lang="ts">
import { computed, ref } from 'vue'
import BaseDialog from '@/components/common/BaseDialog.vue'
import { getFoodDetail, searchFoods } from '@/api/diet'
import type { DietFood } from '@/api/types'

const dialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const keyword = ref('')
const items = ref<DietFood[]>([])
const selected = ref<DietFood | null>(null)
const searching = ref(false)
const loadingDetail = ref(false)
const message = ref('输入食物名称，在薄荷食物库中查询。')
const selectedData = computed(() => selected.value as Record<string, unknown> | null)

function read(keys: string[], labels: RegExp): string {
  const data = selectedData.value
  if (!data) return '未提供'
  const sources = [data, data.nutrition, data.nutrients, data.nutrition_info, data.nutrition_per_100g]
  for (const source of sources) {
    if (Array.isArray(source)) {
      const entry = source.find((item) => {
        if (!item || typeof item !== 'object') return false
        const value = item as Record<string, unknown>
        return labels.test(String(value.name || value.nutrient || value.label || value.title || ''))
      }) as Record<string, unknown> | undefined
      const value = entry?.value ?? entry?.amount ?? entry?.content
      if (typeof value === 'number' || typeof value === 'string') return String(value)
      continue
    }
    if (!source || typeof source !== 'object') continue
    for (const [key, value] of Object.entries(source)) {
      if (keys.includes(key.toLowerCase().replace(/[^a-z0-9]/g, '')) && (typeof value === 'number' || typeof value === 'string')) return String(value)
    }
  }
  return '未提供'
}

function foodName(food: DietFood): string {
  const item = food as Record<string, unknown>
  return String(item.name || item.food_name || item.title || '未命名食物')
}

async function search(): Promise<void> {
  const query = keyword.value.trim()
  if (!query) {
    message.value = '请先输入食物名称。'
    return
  }
  searching.value = true
  selected.value = null
  try {
    const result = await searchFoods(query)
    items.value = result.items
    message.value = result.items.length ? `找到 ${result.items.length} 条食物数据，选择一项查看详情。` : '没有找到结果，请更换关键词。'
  } catch (error) {
    items.value = []
    message.value = error instanceof Error ? error.message : '食物查询失败，请稍后重试。'
  } finally {
    searching.value = false
  }
}

async function viewDetail(food: DietFood): Promise<void> {
  selected.value = food
  const item = food as Record<string, unknown>
  const code = item.code || item.food_code || item.food_id || item.id
  if (!code) return
  loadingDetail.value = true
  try {
    selected.value = (await getFoodDetail(String(code))).food
  } catch (error) {
    message.value = error instanceof Error ? error.message : '详情暂时无法读取，当前显示搜索结果。'
  } finally {
    loadingDetail.value = false
  }
}

function open(): void {
  keyword.value = ''
  items.value = []
  selected.value = null
  message.value = '输入食物名称，在薄荷食物库中查询。'
  dialog.value?.open()
}

defineExpose({ open })
</script>

<template>
  <BaseDialog ref="dialog" class="user-dialog diet-food-library-dialog" aria-labelledby="diet-food-library-title">
    <div class="user-dialog-top">
      <div><p class="eyebrow">FOOD LIBRARY</p><h2 id="diet-food-library-title">搜索食物</h2></div>
      <button class="user-dialog-close" type="button" aria-label="关闭食物库" @click="dialog?.close()">×</button>
    </div>
    <p class="fine-print">在食物库中查询营养信息；此处只查看数据，不会创建餐食记录。</p>
    <form class="diet-food-library-search" @submit.prevent="search">
      <label class="field"><span>食物名称</span><input v-model="keyword" type="search" maxlength="80" placeholder="例如：米饭、鸡蛋" autocomplete="off" /></label>
      <button class="button button-primary" type="submit" :disabled="searching">{{ searching ? '正在查询…' : '搜索' }}</button>
    </form>
    <p class="fine-print" aria-live="polite">{{ message }}</p>
    <div v-if="items.length" class="diet-food-search-results">
      <button v-for="(food,index) in items" :key="String((food as Record<string, unknown>).code || food.id || index)" class="diet-food-result" :class="{ selected: selected === food }" type="button" @click="viewDetail(food)">
        <strong>{{ foodName(food) }}</strong><small>每 100 克 · {{ String((food as Record<string, unknown>).calories_kcal ?? (food as Record<string, unknown>).kcal ?? '营养详情可查看') }}</small>
      </button>
    </div>
    <section v-if="selected" class="diet-food-library-detail" aria-live="polite">
      <h3>{{ foodName(selected) }} <small>{{ loadingDetail ? '正在读取详情…' : '每 100 克' }}</small></h3>
      <dl>
        <div><dt>热量</dt><dd>{{ read(['calorieskcal','caloriekcal','kcal','calories','energy'], /energy|calor|能量|热量/i) }} kcal</dd></div>
        <div><dt>蛋白质</dt><dd>{{ read(['proteing','protein'], /protein|蛋白/i) }} g</dd></div>
        <div><dt>碳水</dt><dd>{{ read(['carbsg','carbs','carbohydrate','carbohydrates'], /carb|碳水/i) }} g</dd></div>
        <div><dt>脂肪</dt><dd>{{ read(['fatg','fat'], /fat|脂肪/i) }} g</dd></div>
      </dl>
    </section>
  </BaseDialog>
</template>
