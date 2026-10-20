<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getCurrentPlan } from '@/api/today'
import type { CurrentPlanResponse } from '@/api/types'

const router = useRouter()
const result = ref<CurrentPlanResponse | null>(null)
const error = ref<string | null>(null)

onMounted(async () => {
  try { result.value = await getCurrentPlan() }
  catch (cause) { error.value = cause instanceof Error ? cause.message : '暂时无法读取本周计划。' }
})

function planText(plan: Record<string, unknown>): string {
  const sessions = Array.isArray(plan.sessions) ? plan.sessions as Array<{ title?: string }> : []
  return sessions.map((session) => session.title).filter(Boolean).join(' / ')
}
</script>

<template>
  <article class="panel plan-peek">
    <div class="panel-head"><div><p class="eyebrow">YOUR PLAN</p><h3>本周计划</h3></div><span class="step-no">02</span></div>
    <div v-if="result?.week_plan" class="plan-summary-mini">
      <b>{{ result.week_plan.focus }} · 每周 {{ result.week_plan.days_per_week }} 天</b>
      <p>{{ planText(result.week_plan) }}</p>
      <button class="text-button" type="button" @click="router.push({ name: 'plan' })">查看计划 →</button>
    </div>
    <div v-else class="empty-state">
      <p>{{ error || '选择训练星期并生成一份基础周计划。' }}</p>
      <button class="text-button" type="button" @click="router.push({ name: 'plan' })">前往周计划 →</button>
    </div>
  </article>
</template>
