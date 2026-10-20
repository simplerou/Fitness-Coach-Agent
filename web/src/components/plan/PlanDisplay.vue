<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { usePlanStore } from '@/stores/plan'
import { localDateString, shiftDate } from '@/utils/date'
import { useTrainingStore } from '@/stores/training'
import ExerciseDetailDialog from '@/components/training/ExerciseDetailDialog.vue'
import type { ExerciseDefinition } from '@/api/types'

const planStore = usePlanStore()
const training = useTrainingStore()
const activeExercise = ref<ExerciseDefinition | null>(null)
onMounted(() => { if (!training.exercises.length) void training.loadExercises() })
function showExercise(id: number): void { activeExercise.value = training.exercises.find((item) => item.id === id) || null }
const plan = computed(() => planStore.selectedPlan)
const weekStart = computed(() => planStore.selectedWeek || planStore.currentWeekStart || localDateString())
const weekdayNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const experience = { beginner: '刚开始训练', some_experience: '有一些经验', experienced: '经验较丰富' }
const equipment: Record<string, string> = { bodyweight_only: '仅自重', dumbbells: '哑铃', resistance_bands: '弹力带', gym: '健身房常见器械' }
const sessions = computed(() => {
  if (!plan.value) return []
  const items = plan.value.sessions ?? []
  return planStore.todayPaused && !planStore.selectedIsHistorical ? items.filter((session) => session.weekday !== planStore.selectedWeekday) : items
})
const setup = computed(() => plan.value ? `${experience[plan.value.experience_level]} · ${plan.value.equipment.map((item) => equipment[item] || item).join('、')} · 约 ${plan.value.session_minutes} 分钟/次` : '')
</script>

<template>
  <article class="panel result-panel">
    <div class="panel-head"><div><p class="eyebrow">PLAN PREVIEW</p><h3>{{ planStore.selectedIsHistorical ? '历史计划预览' : '计划预览' }}</h3></div></div>
    <div v-if="!plan" class="empty-state"><div class="empty-icon">✳</div><p>你的周计划会显示在这里。</p></div>
    <div v-else class="plan-result">
      <div class="history-plan-banner" :class="{ 'current-plan-banner': !planStore.selectedIsHistorical }">{{ planStore.selectedIsHistorical ? `历史计划，仅供回看 · ${weekStart} 至 ${shiftDate(weekStart, 6)}，不代表本周训练建议。` : `当前周计划 · ${weekStart} 至 ${shiftDate(weekStart, 6)}` }}</div>
      <div v-if="planStore.todayPaused && !planStore.selectedIsHistorical" class="safety-stop-note">今天的训练安排已暂停；本周其他安排仍可查看。</div>
      <div v-if="plan.training_weekdays" class="week-schedule" role="group" aria-label="本周训练与休息日">
        <div v-for="(day, index) in weekdayNames" :key="day" class="weekday-card" :class="index + 1 === planStore.selectedWeekday && planStore.todayPaused && !planStore.selectedIsHistorical ? 'paused-day' : plan.training_weekdays.includes(index + 1) ? 'training-day' : 'rest-day'">
          <b>{{ day }}</b><span>{{ index + 1 === planStore.selectedWeekday && planStore.todayPaused && !planStore.selectedIsHistorical ? '今日暂停' : plan.training_weekdays.includes(index + 1) ? '训练' : '休息' }}</span>
        </div>
      </div>
      <div class="plan-meta"><span>{{ plan.focus }}</span><span>每周 {{ plan.days_per_week }} 天</span></div>
      <p v-if="setup" class="fine-print">本周设置：{{ setup }}</p>
      <div class="explanation-block"><h4>{{ planStore.selectedIsHistorical ? '当周安排' : '本周安排' }}</h4>
        <ul v-if="sessions.length" class="explanation-session-list"><li v-for="session in sessions" :key="`${session.weekday}-${session.title}`"><b>{{ session.day }} · {{ session.title }}{{ session.duration_minutes ? ` · 约 ${session.duration_minutes} 分钟` : '' }}</b><span>{{ session.description }}</span><div v-if="session.exercises?.length" class="plan-session-exercises"><button v-for="item in session.exercises" :key="item.id" type="button" @click="showExercise(item.id)">{{ item.name }} · 查看要领</button></div></li></ul>
        <p v-else>当前计划没有训练日条目。</p>
      </div>
      <div class="explanation-block"><h4>执行时可以留意</h4><ul><li>开始前先查看计划中的训练内容和动作说明，按自己能够控制的节奏进行。</li><li>计划是通用模板，不要求为了补上未完成的训练而临时加量。</li><li>如果训练中出现明显不适，请停止训练；症状严重、持续或加重时，及时寻求专业帮助。</li></ul></div>
      <p class="fine-print">{{ plan.notice }}</p>
      <p class="plan-storage-note">{{ planStore.selectedIsHistorical ? '这是已保存的历史计划，仅供回看。' : `本周计划已保存到本机 PostgreSQL。${planStore.savedAt ? `保存时间：${planStore.savedAt}` : ''} 服务重启后仍可查看，今日确认只影响当天训练安排。` }}</p>
    </div>
    <ExerciseDetailDialog :exercise="activeExercise" @close="activeExercise = null" />
  </article>
</template>
