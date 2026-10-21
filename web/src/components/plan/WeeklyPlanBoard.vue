<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import { useNotice } from '@/composables/useNotice'
import { usePlanStore } from '@/stores/plan'
import { shiftDate } from '@/utils/date'
import type { PlanSessionItem } from '@/api/types'

const plan = usePlanStore()
const notice = useNotice()
const draft = ref<PlanSessionItem[]>([])
const dragging = ref<number | null>(null)
const confirmOpen = ref(false)
const weekdayNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const weekStart = computed(() => plan.currentWeekStart || plan.selectedWeek || '')
const changed = computed(() => draft.value.filter((item) => {
  const source = plan.currentPlan?.sessions.find((session) => session.title === item.title)
  return source && source.weekday !== item.weekday
}).length)
watch(() => plan.currentPlan, (value) => { draft.value = value?.sessions.map((item) => ({ ...item })) ?? [] }, { immediate: true, deep: true })
function sessionsFor(day: number) { return draft.value.filter((item) => item.weekday === day) }
function drop(day: number) { const item = dragging.value == null ? null : draft.value[dragging.value]; if (item) item.weekday = day; dragging.value = null }
function reset() { draft.value = plan.currentPlan?.sessions.map((item) => ({ ...item })) ?? [] }
async function apply() {
  confirmOpen.value = false
  plan.preferences.training_weekdays = [...new Set(draft.value.map((item) => item.weekday))].sort()
  plan.preferences.days_per_week = plan.preferences.training_weekdays.length
  try { notice.notify(await plan.create(), 'success') } catch (error) { notice.notify(error instanceof Error ? error.message : '暂时无法重新生成计划。', 'error') }
}
</script>

<template>
  <div v-if="changed" class="draft-banner" role="status"><span>已调整 {{ changed }} 天，变更仅在本页草稿中。</span><div><button class="text-button" @click="reset">撤销</button><button class="button button-primary" @click="confirmOpen = true">按此重新生成</button></div></div>
  <div v-if="!plan.currentPlan" class="empty-state"><strong>还没有本周计划</strong><span>在下方设置训练偏好后生成第一份计划。</span></div>
  <div v-else class="week-board">
    <section v-for="day in 7" :key="day" class="week-column" @dragover.prevent @drop="drop(day)">
      <header><b>{{ weekdayNames[day - 1] }}</b><span>{{ weekStart ? shiftDate(weekStart, day - 1).slice(5) : '' }}</span></header>
      <article v-for="session in sessionsFor(day)" :key="session.title" class="session-tile" draggable="true" @dragstart="dragging = draft.indexOf(session)">
        <span class="session-status" />
        <h3>{{ session.title }}</h3>
        <p>{{ session.duration_minutes }} 分钟 · {{ session.exercises?.length ?? 0 }} 个动作</p>
        <small>{{ session.description }}</small>
      </article>
      <div v-if="!sessionsFor(day).length" class="rest-tile">休息日</div>
    </section>
  </div>
  <ConfirmDialog v-model:open="confirmOpen" title="覆盖本周计划？" description="后端只支持整周生成。确认后会根据新的训练日重新生成并覆盖本周计划。" confirm-text="确认重新生成" danger @confirm="apply" />
</template>
