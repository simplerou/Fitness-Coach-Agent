<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDietStore } from '@/stores/diet'
import { useHomeStore } from '@/stores/home'
import { useSafetyStore } from '@/stores/safety'
import { useShapingIntelligenceStore } from '@/stores/shapingIntelligence'
import { useNotice } from '@/composables/useNotice'
import { localDateString } from '@/utils/date'

const router = useRouter()
const home = useHomeStore()
const safety = useSafetyStore()
const diet = useDietStore()
const intelligence = useShapingIntelligenceStore()
const notice = useNotice()
const schedule = computed(() => safety.today?.today_schedule ?? null)
const session = computed(() => schedule.value?.session ?? null)
const completed = computed(() => home.todayLog?.completion === 'completed')
const suggestion = computed(() => intelligence.dietAdjustment?.suggestion ?? null)
const dietStatus = computed(() => intelligence.dietAdjustment?.status ?? 'needs_data')
const dayLabel = computed(() => ({ training: '训练日', rest: '休息日', recovery: '恢复日' })[intelligence.dietAdjustment?.day_type ?? 'rest'])
const trainingTitle = computed(() => {
  if (schedule.value?.status === 'training' && session.value) return session.value.title
  if (schedule.value?.status === 'rest') return '让恢复成为计划的一部分'
  return '还没有今天的训练安排'
})
const trainingDescription = computed(() => {
  if (schedule.value?.status === 'training' && session.value) return `${session.value.duration_minutes ? `约 ${session.value.duration_minutes} 分钟 · ` : ''}${session.value.description}`
  if (schedule.value?.status === 'rest') return '今天无需提交训练状态，按当前周计划安排恢复。'
  return '先生成本周计划，首页会自动定位今天的训练。'
})
const trainingButton = computed(() => {
  if (completed.value) return '今天已完成'
  if (schedule.value?.status === 'training') return '开始训练'
  if (schedule.value?.status === 'rest') return '查看本周计划'
  return '创建周计划'
})

function continueTraining(): void {
  if (schedule.value?.status === 'training') void router.push({ name: 'log' })
  else void router.push({ name: 'plan' })
}
async function adoptDiet(): Promise<void> {
  try {
    const message = await intelligence.decideDiet(intelligence.dietAdjustment?.date ?? localDateString(), 'adopted')
    notice.notify(message, 'success')
  } catch (error) { notice.notify(error instanceof Error ? error.message : '请求失败，请稍后重试。', 'error') }
}
</script>

<template>
  <div class="home-action-grid">
    <article class="home-action-card home-training-card">
      <div class="home-action-top"><span>今日训练</span><span class="home-state" :class="{ done: completed }">{{ completed ? '已完成' : schedule?.status === 'rest' ? '计划休息' : '待行动' }}</span></div>
      <strong class="home-action-value">{{ trainingTitle }}</strong>
      <p>{{ trainingDescription }}</p>
      <button class="button" :class="completed ? 'button-quiet' : 'button-primary'" :disabled="safety.loading || completed" @click="continueTraining">{{ trainingButton }}</button>
    </article>

    <article class="home-action-card home-diet-card">
      <div class="home-action-top"><span>今日饮食 · {{ dayLabel }}</span><span class="home-state" :class="{ done: dietStatus === 'adopted' }">{{ dietStatus === 'adopted' ? '已采纳' : '待确认' }}</span></div>
      <template v-if="suggestion">
        <div class="home-nutrition-number"><strong>{{ suggestion.calories_kcal }}</strong><span>kcal</span><b>蛋白 {{ suggestion.protein_g }} g</b></div>
        <p>{{ suggestion.reason }}</p>
        <button v-if="dietStatus !== 'adopted'" class="button button-primary" @click="adoptDiet">采纳为今日参考</button>
        <button v-else class="button button-quiet" @click="router.push({ name: 'diet' })">去记录饮食</button>
      </template>
      <template v-else>
        <strong class="home-action-value">饮食目标还不能计算</strong>
        <p>{{ intelligence.dietAdjustment?.message || diet.targets?.message || '补齐身体和饮食档案后生成训练日/休息日建议。' }}</p>
        <button class="button button-primary" @click="router.push({ name: 'diet' })">完善饮食档案</button>
      </template>
    </article>
  </div>

</template>
