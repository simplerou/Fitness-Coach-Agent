<script setup lang="ts">
import { computed } from 'vue'
import { useDietStore } from '@/stores/diet'

const diet = useDietStore()
const emit = defineEmits<{ generate: []; 'open-profile': [] }>()
const result = computed(() => diet.plan)
const ready = computed(() => result.value?.status === 'ready')
const summary = computed(() => result.value?.summary || {})
const target = computed(() => result.value?.target || {})
const records = computed(() => result.value?.record_summary || {})
const ai = computed(() => result.value?.ai_advice || {})
const number = (value: unknown, digits = 0): string => value == null || value === '' ? '未记录' : Number(value).toLocaleString('zh-CN', { maximumFractionDigits: digits })
const dateText = (value: unknown): string => typeof value === 'string' ? value : ''
const formatMetric = (label: string, value: unknown, unit = '') => `${label} · ${number(value, 1)}${unit}`
const weeklyDays = computed(() => {
  if (Array.isArray(result.value?.weekly_plan) && result.value.weekly_plan.length) return result.value.weekly_plan
  return [{ date: '', weekday: '每日参考', day_type: '通用安排', meals: (result.value?.meal_plan || []).map((meal) => ({ ...meal, example: result.value?.food_examples?.find((food) => food.meal === meal.name)?.example || '' })) }]
})
function list(value: unknown): string[] { return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [] }
function chooseHistory(index: number): void { diet.plan = diet.planHistory[index]?.plan_data || null }
</script>

<template>
  <article class="panel diet-plan-panel">
    <div class="panel-head"><div><p class="eyebrow">AI DIET PLANNING</p><h3>一周饮食计划</h3></div><button class="button button-primary" type="button" :disabled="diet.generatingPlan" @click="emit('generate')">更新本周计划</button></div>
    <p class="fine-print diet-refresh-note">初次根据身体档案和饮食偏好生成；之后可结合近 7 天餐食、饮水、训练和体重记录更新计划。营养目标由后端公式计算，AI 负责安排不同餐次的食物示例；记录食物后，系统按食物库和分量计算实际营养。每次更新都会保存历史快照。</p>
    <div v-if="!result" class="empty-state"><p>先完善身体档案与饮食规划档案，即可生成初始计划；之后记录每日餐食，在下方查看实际摄入与目标的差距。</p><button class="button button-primary" type="button" @click="emit('open-profile')">完善档案并设置计划</button></div>
    <div v-else-if="!ready" class="empty-state"><p>{{ result.message || (result.status === 'professional_support' ? '当前情况需要先咨询医生或注册营养师。' : '请补充所需资料后再生成，不会用猜测值代替。') }}</p><ul v-if="result.missing?.length"><li v-for="item in result.missing" :key="item">{{ item }}</li></ul><button class="button button-primary" type="button" @click="emit('open-profile')">完善档案并设置计划</button></div>
    <div v-else class="diet-plan-result">
      <section class="diet-ai-advice"><h4>AI 饮食洞察</h4><p>{{ ai.overview || '这份历史记录尚未包含 AI 洞察。' }}</p><p class="diet-change-summary">{{ ai.change_summary || result.change_summary || '计划更新时会说明本次调整依据。' }}</p><template v-for="[title, values] in [['结合记录的观察', ai.diagnosis], ['训练时段建议', ai.training_timing_advice]]" :key="title"><h5 v-if="list(values).length">{{ title }}</h5><ul v-if="list(values).length"><li v-for="(entry, index) in list(values)" :key="index">{{ entry }}</li></ul></template></section>
      <section><h4>数据摘要与依据</h4><div class="diet-metrics"><div class="diet-metric">{{ formatMetric('身高', summary.height_cm, ' cm') }}</div><div class="diet-metric">{{ formatMetric('体重', summary.weight_kg, ' kg') }}</div><div class="diet-metric">{{ formatMetric('BMI（成人参考）', summary.bmi) }}</div><div class="diet-metric">{{ formatMetric('估算 BMR', summary.bmr_kcal, ' kcal') }}</div><div class="diet-metric">{{ formatMetric('估算 TDEE', summary.tdee_kcal, ' kcal') }}</div></div><p>{{ summary.goal }}；活动水平：{{ summary.activity_level }}。BMR 来源：{{ summary.bmr_source }}；TDEE 来源：{{ summary.tdee_source }}。</p><p>近期完整记录：{{ number(records.coverage?.days_marked_complete) }} 天。{{ target.basis }}</p></section>
      <section><h4>近期记录概况</h4><p>近 7 天记录餐次：早餐 {{ number(records.meal_distribution?.counts?.早餐) }}、午餐 {{ number(records.meal_distribution?.counts?.午餐) }}、晚餐 {{ number(records.meal_distribution?.counts?.晚餐) }}、加餐 {{ number(records.meal_distribution?.counts?.加餐) }}；填写进食时间 {{ number(records.meal_distribution?.timed_meals) }} 餐，填写分量 {{ number(records.meal_distribution?.meals_with_portion) }} 餐。</p><p>饮水记录：{{ number(records.hydration?.days_logged) }} 天；累计 {{ number(records.hydration?.total_ml) }} 毫升；有记录日均 {{ number(records.hydration?.average_on_logged_days_ml) }} 毫升；{{ records.hydration?.target_ml ? `个人参考目标 ${number(records.hydration.target_ml)} 毫升/日` : '未设置个人目标' }}。未记录日不作零值处理，也不据此判断是否缺水。</p><p>训练日完整碳水均值：{{ number(records.training_day_comparison?.training_day_carbs_g) }} g（{{ number(records.training_day_comparison?.training_days_with_data) }} 天）；休息日：{{ number(records.training_day_comparison?.rest_day_carbs_g) }} g（{{ number(records.training_day_comparison?.rest_days_with_data) }} 天）。</p></section>
      <section><h4>主要差距与提醒</h4><ul v-if="list(result.diagnosis).length"><li v-for="(item, index) in list(result.diagnosis)" :key="index">{{ item }}</li></ul><p v-else>暂无额外提示。</p><template v-if="list(result.warnings).length"><h5>数据质量与安全提醒</h5><ul><li v-for="item in list(result.warnings)" :key="item">{{ item }}</li></ul></template></section>
      <section><h4>每日目标起点</h4><div class="diet-metrics"><div class="diet-metric">{{ formatMetric('能量', target.calories_kcal, ' kcal') }}</div><div class="diet-metric">{{ formatMetric('蛋白质', target.protein_g, ' g') }}</div><div class="diet-metric">{{ formatMetric('碳水', target.carbs_g, ' g') }}</div><div class="diet-metric">{{ formatMetric('脂肪', target.fat_g, ' g') }}</div></div><p>能量占比约：蛋白质 {{ number(target.protein_percent) }}%、碳水 {{ number(target.carbs_percent) }}%、脂肪 {{ number(target.fat_percent) }}%。</p></section>
      <section><h4>体重趋势与目标进度</h4><p>{{ Array.isArray(summary.weight_trend_14d) && summary.weight_trend_14d.length >= 2 ? `近 14 天有 ${summary.weight_trend_14d.length} 次体重记录，首末记录变化 ${Number(summary.weight_change_14d) > 0 ? '+' : ''}${number(summary.weight_change_14d, 1)} kg（仅描述首末记录，不代表趋势或原因）。` : Array.isArray(summary.weight_trend_14d) && summary.weight_trend_14d.length === 1 ? '近 14 天只有 1 次体重记录，暂时不能判断变化。' : '近 14 天没有体重记录，暂时不能判断变化。' }}</p><p>{{ summary.target_weight_kg == null ? '你尚未设置体重目标；可以留空，系统不会替你设定。' : `当前档案体重 ${number(summary.weight_kg, 1)} kg，距你自设目标 ${number(Math.abs(Number(summary.weight_kg) - Number(summary.target_weight_kg)), 1)} kg。目标仅用于追踪，不用于推算达成时间。` }}</p><small>体重数据来源：你记录的体重历史；记录点不足时不计算变化。体重短期波动不能单独说明脂肪或肌肉变化。</small></section>
      <section><h4>一周餐次建议</h4><p>每日目标保持一致，餐次例子会结合训练安排与近期记录轮换；未绑定营养数据库的例子不显示精确营养值。</p><div class="diet-week-plan"><details v-for="(day, index) in weeklyDays" :key="`${dateText(day.date)}-${index}`" class="diet-day-plan" :open="index === 0"><summary><span><b>{{ day.weekday || '计划日' }}</b><small>{{ dateText(day.date) }}</small></span><span class="tag">{{ day.day_type || '参考安排' }}</span></summary><div class="diet-day-meals"><article v-for="meal in day.meals || []" :key="meal.name"><div><b>{{ meal.name }}</b><small>本餐分配目标：{{ number(meal.calories_kcal) }} kcal · 蛋白质 {{ number(meal.protein_g) }}g · 碳水 {{ number(meal.carbs_g) }}g · 脂肪 {{ number(meal.fat_g) }}g</small></div><p><b>搭配示例：</b>{{ meal.example || '' }}</p></article></div></details></div></section>
      <section><h4>现有习惯与调整</h4><p><b>可保留：</b>{{ result.recorded_habits?.keep || '' }}</p><p><b>优先调整：</b>{{ result.recorded_habits?.adjust || '' }}</p><p>{{ result.execution_context?.cooking_access || '' }}；每周外食 {{ number(result.execution_context?.eating_out_per_week) }} 次；执行条件：{{ result.execution_context?.budget_note || '未填写' }}。</p></section>
      <section><h4>追踪与计算说明</h4><p>{{ result.tracking?.period || '' }}</p><ul v-if="list(result.tracking?.next_data).length"><li v-for="item in list(result.tracking?.next_data)" :key="item">{{ item }}</li></ul><details><summary>查看数据假设与边界</summary><ul><li v-for="item in list(result.assumptions)" :key="item">{{ item }}</li></ul></details></section>
    </div>
    <article class="panel diet-history-panel"><div class="panel-head"><div><p class="eyebrow">SAVED REVIEWS</p><h3>近期规划记录</h3></div><button class="text-button" type="button" @click="diet.loadHistory">刷新</button></div><div v-if="diet.planHistory.length" class="diet-history-list"><button v-for="(item,index) in diet.planHistory" :key="item.id" class="diet-history-item" type="button" @click="chooseHistory(index)"><strong>{{ new Date(item.created_at).toLocaleString('zh-CN') }}</strong><span>{{ item.plan_data.summary?.goal || '饮食规划' }} · {{ number(item.plan_data.target?.calories_kcal) }} kcal/日</span></button></div><p v-else class="empty-state">生成规划后，会保留历史快照供你对比。</p></article>
  </article>
</template>

