<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useReviewStore } from '@/stores/review'
import { usePlanStore } from '@/stores/plan'
import { useNotice } from '@/composables/useNotice'
import { shiftDate } from '@/utils/date'
import PlanAdjustmentPreview from '@/components/training/PlanAdjustmentPreview.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import ReportTabs from '@/components/shaping/ReportTabs.vue'

const review = useReviewStore()
const plan = usePlanStore()
const notice = useNotice()
const router = useRouter()
withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false })
const result = computed(() => review.result)
const summary = computed(() => result.value?.summary)
const previousDisabled = computed(() => Boolean(result.value && shiftDate(result.value.week_start, -1) < result.value.registration_date))
const completionLabels = { completed: '按计划完成', partial: '部分完成', skipped: '未进行训练' }
const reasonLabels = { no_time: '没时间', too_tired: '太累', discomfort: '身体不适', other: '其他' }
const mealLabels: Record<string, string> = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '加餐' }

onMounted(() => { void review.load() })

function guidance(): string {
  const s = summary.value
  if (!s) return ''
  const plannedRecorded = s.planned_elapsed_day_count - s.planned_unlogged_count
  if (!s.planned_day_count) return '这周没有可对照的已保存周计划。生成周计划并记录训练后，周回顾会展示执行情况。'
  if (!s.planned_elapsed_day_count) return '本周计划尚未开始，或计划训练日还未到。等训练日经过并记录情况后，再参考本周数据调整。'
  if (!plannedRecorded) return '本周已到的计划训练日目前都还没有对应记录。先记录实际完成情况，再决定是否调整下周安排。'
  if (s.planned_skipped_count > s.planned_completed_count + s.planned_partial_count) return '本周未进行的计划日多于完成或部分完成的计划日。下周可考虑减少训练日或缩短单次时长；也可以结合实际原因自行决定。'
  if (s.average_rpe != null && s.average_rpe >= 8) return `本周平均主观用力程度为 ${s.average_rpe} / 10。下周可考虑维持或减少训练天数、单次时长，按恢复感受自行调整。`
  if (s.planned_unlogged_count > 0) return `截至今天，已到的计划训练日：完成 ${s.planned_completed_count} 天、部分完成 ${s.planned_partial_count} 天、未进行 ${s.planned_skipped_count} 天、未记录 ${s.planned_unlogged_count} 天。补充记录能让下周回顾更准确。`
  return '截至今天已到的计划训练日都有记录。可以结合完成情况和用力感保持或微调下周安排；系统不会自动增加训练量。'
}

async function applySuggestion(): Promise<void> {
  const s = summary.value
  if (!s) return
  await plan.loadPreferences()
  const shorten = (): boolean => {
    const next = ({ 60: 45, 45: 30, 30: 20 } as Record<number, number>)[plan.preferences.session_minutes]
    if (!next) return false
    plan.preferences.session_minutes = next as 20 | 30 | 45 | 60
    return true
  }
  const reduceDays = (): boolean => {
    if (plan.preferences.training_weekdays.length <= 1) return false
    plan.preferences.training_weekdays = plan.preferences.training_weekdays.slice(0, -1)
    plan.preferences.days_per_week = plan.preferences.training_weekdays.length
    return true
  }
  const changed = s.planned_skipped_count > s.planned_completed_count + s.planned_partial_count
    ? (reduceDays() || shorten()) : (shorten() || reduceDays())
  if (!changed) { notice.notify('当前训练时长和训练日数已处于可选下限，建议先保持安排，并结合恢复情况再决定。'); return }
  plan.edited = true
  await router.push({ name: 'plan' })
  notice.notify('已把本周回顾建议带入计划设置。检查训练日和时长后，再手动生成下周计划。')
}
</script>

<template>
  <section class="page active">
    <template v-if="!embedded"><PageHeader title="周回顾" :breadcrumbs="['报告', '周回顾']" description="缺失数据会明确标记为未记录"/><ReportTabs /></template>
    <article class="panel review-controls"><div class="panel-head"><div><p class="eyebrow">WEEK RANGE</p><h3>{{ result ? `${result.week_start} 至 ${result.week_end}` : '选择回顾日期' }}</h3></div></div><div class="review-date-controls"><button class="button button-quiet" type="button" :disabled="previousDisabled" @click="review.moveWeek(-1)">上一周</button><label class="field"><span>选择日期</span><input v-model="review.selectedDate" type="date" @change="review.load" /></label><button class="button button-quiet" type="button" @click="review.currentWeek">本周</button><button class="button button-quiet" type="button" :disabled="review.loading" @click="review.load">刷新</button></div><p v-if="result" id="review-range" class="fine-print">可查看自 {{ result.registration_date }}</p><p v-if="review.error" class="review-error" role="alert">{{ review.error }}</p></article>
    <div v-if="summary" id="review-stats" class="review-stats">
      <article v-for="item in [['日志条数', `${summary.session_count} 条`], ['按计划完成', `${summary.completed_count} 次`], ['部分完成', `${summary.partial_count} 次`], ['未进行', `${summary.skipped_count} 次`], ['平均 RPE', summary.average_rpe == null ? `未记录（${summary.rpe_count} 条）` : `${summary.average_rpe} / 10（${summary.rpe_count} 条）`], ['饮食记录', `${summary.diet_meal_count} 餐 · ${summary.diet_days_with_meals} 天`], ['饮水记录', summary.diet_water_total_ml == null ? '未记录' : `${summary.diet_water_total_ml} 毫升 · ${summary.diet_water_days_logged} 天`], ['饮食完整日', `${summary.diet_days_marked_complete} 天`], ['体重记录', `${summary.weight_days_logged} 天`]]" :key="item[0]" class="panel review-stat"><span>{{ item[0] }}</span><b>{{ item[1] }}</b></article>
    </div>
    <article v-if="result" id="review-guidance" class="panel review-guidance"><b>下周调整参考</b><p>{{ guidance() }}</p><p class="review-data-context">本周饮食记录 {{ summary?.diet_meal_count }} 餐、{{ summary?.diet_days_with_meals }} 天；体重记录 {{ summary?.weight_days_logged }} 天。它们用于回顾生活状态，不会单独推断训练强度或营养目标。</p><template v-if="summary && summary.planned_day_count && summary.planned_elapsed_day_count - summary.planned_unlogged_count > 0 && (summary.planned_skipped_count > summary.planned_completed_count + summary.planned_partial_count || (summary.average_rpe != null && summary.average_rpe >= 8))"><button class="button button-primary review-apply" type="button" @click="applySuggestion">将建议带入计划设置</button><span class="review-apply-note">带入后可检查或修改，再手动生成计划。</span></template></article>
    <PlanAdjustmentPreview v-if="result" :week-of="review.selectedDate" />
    <div v-if="result" id="review-days" class="review-days">
      <article v-for="(day, index) in result.days" :key="day.date" class="panel review-day">
        <div class="review-day-head"><b>{{ ['周一','周二','周三','周四','周五','周六','周日'][index] }} · {{ day.date }}</b><span class="review-planned-label">{{ day.before_registration ? '注册前：不适用' : day.planned_session_title ? `计划训练：${day.planned_session_title}` : day.plan_status === 'training' ? '计划训练安排暂不可用' : day.plan_status === 'rest' ? '计划休息日' : day.plan_status === 'legacy_plan' ? '旧计划未记录具体训练日' : '无周计划' }}</span></div>
        <p class="review-signal">{{ day.before_registration ? '注册前：不适用' : day.signal ? `${{ good: '状态不错', okay: '一般', poor: '状态较差' }[day.signal.readiness]} · 睡眠 ${day.signal.sleep_hours == null ? '未记录' : `${day.signal.sleep_hours} 小时`} · 静息心率 ${day.signal.resting_hr == null ? '未记录' : `${day.signal.resting_hr} 次/分`}` : '状态：未记录' }}</p>
        <div class="review-log-list">{{ day.before_registration ? '注册前：不适用' : day.logs.length ? '' : '训练日志：未记录' }}<article v-for="(entry, i) in day.logs" :key="i" class="review-log"><b>{{ completionLabels[entry.completion] }}</b><span>{{ entry.rpe == null ? 'RPE 未记录' : `RPE ${entry.rpe}` }}{{ entry.skip_reason ? ` · ${reasonLabels[entry.skip_reason]}` : '' }}</span><p v-if="entry.note">{{ entry.note }}</p></article></div>
        <div v-if="!day.before_registration" class="review-diet-summary"><b>饮食与身体记录</b><span>{{ day.diet.meals.length ? day.diet.meals.map((meal) => `${mealLabels[meal.meal_type] || '餐食'}：${meal.description}`).join(' · ') : '餐食未记录' }}</span><span>{{ day.diet.calories_kcal == null ? '热量未记录' : `热量 ${day.diet.calories_kcal} 千卡（${day.diet.calories_logged_count}/${day.diet.meal_count} 餐填写）` }} · {{ day.diet.protein_g == null ? '蛋白质未记录' : `蛋白质 ${day.diet.protein_g}g` }} · {{ day.diet.carbs_g == null ? '碳水未记录' : `碳水 ${day.diet.carbs_g}g` }} · {{ day.diet.fat_g == null ? '脂肪未记录' : `脂肪 ${day.diet.fat_g}g` }}</span><span>{{ day.diet.water_ml == null ? '饮水未记录' : `饮水 ${day.diet.water_ml} 毫升` }} · {{ day.diet.complete == null ? '完整度未标记' : day.diet.complete ? '已标记饮食记录完整' : '饮食记录尚未标记完整' }} · {{ day.weight_kg == null ? '体重未记录' : `体重 ${day.weight_kg} 千克` }}</span></div>
        <div v-else class="review-diet-summary">饮食、饮水与体重：注册前不适用</div>
      </article>
    </div>
  </section>
</template>
