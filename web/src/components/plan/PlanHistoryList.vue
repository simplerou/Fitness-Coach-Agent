<script setup lang="ts">
import { usePlanStore } from '@/stores/plan'
import { shiftDate } from '@/utils/date'

const plan = usePlanStore()
</script>

<template>
  <article class="panel plan-history-panel">
    <div class="panel-head"><div><p class="eyebrow">SAVED WEEKS</p><h3>历史周计划</h3></div><button class="text-button" type="button" :disabled="plan.historyLoading" @click="plan.loadHistory()">刷新</button></div>
    <p class="fine-print">只显示本地档案起始周及之后实际保存的计划。查看历史计划不需要进行今日训练确认。</p>
    <div v-if="!plan.history.length" class="plan-history-list empty-state"><p>{{ plan.historyLoading ? '正在读取已保存计划…' : '还没有可查看的已保存周计划。' }}</p></div>
    <div v-else class="plan-history-list">
      <button v-for="item in plan.history" :key="item.week_start" class="plan-history-item" :class="{ selected: plan.selectedWeek === item.week_start }" type="button" :aria-pressed="plan.selectedWeek === item.week_start" @click="plan.selectedWeek = item.week_start">
        <span class="plan-history-top"><b>{{ item.week_start }} 至 {{ item.week_end || shiftDate(item.week_start, 6) }}</b><span class="tag" :class="{ 'history-tag': item.week_start !== plan.currentWeekStart }">{{ item.week_start === plan.currentWeekStart ? '本周' : '历史' }}</span></span>
        <span class="plan-history-meta">{{ item.week_plan.focus }} · 每周 {{ item.week_plan.days_per_week }} 天</span><span class="plan-history-saved">保存时间：{{ item.saved_at }}</span>
      </button>
    </div>
    <button v-if="plan.historyCursor" class="button button-quiet" type="button" :disabled="plan.historyLoading" @click="plan.loadHistory(false)">加载更早计划</button>
  </article>
</template>
