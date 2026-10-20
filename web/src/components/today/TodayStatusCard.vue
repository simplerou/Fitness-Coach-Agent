<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useSafetyStore } from '@/stores/safety'

const safety = useSafetyStore()
const router = useRouter()
const today = computed(() => safety.today)
const label = computed(() => today.value ? safety.levelLabel(today.value.level) : ['状态未知', ''] as [string, string])
const showSchedule = computed(() => today.value?.level === 'normal' || today.value?.level === 'rest_day')
const weekdayNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
</script>

<template>
  <article class="status-card" :class="today ? `status-${today.level}` : 'status-ask'" aria-live="polite">
    <template v-if="safety.loading && !today">
      <div class="loading-dot"></div><span>正在读取当前状态…</span>
    </template>
    <template v-else-if="today">
      <div class="status-top"><span class="status-pill"><i></i>{{ label[0] }}</span><span class="status-detail">{{ label[1] }}</span></div>
      <h3>{{ today.message }}</h3>
      <ul class="reason-list"><li v-for="reason in today.reasons" :key="reason">{{ reason }}</li></ul>
      <div v-if="showSchedule && today.today_schedule" class="today-schedule" :class="today.today_schedule.status === 'training' ? 'training-day' : today.today_schedule.status === 'rest' ? 'rest-day' : 'no-plan'">
        <template v-if="today.today_schedule.status === 'training' && today.today_schedule.session">
          <span class="today-schedule-label">今日训练 · {{ weekdayNames[today.today_schedule.weekday - 1] || '今天' }}</span>
          <b>{{ today.today_schedule.session.title }}{{ today.today_schedule.session.duration_minutes ? ` · 约 ${today.today_schedule.session.duration_minutes} 分钟` : '' }}</b>
          <p>{{ today.today_schedule.session.description }}</p>
        </template>
        <template v-else-if="today.today_schedule.status === 'rest'">
          <span class="today-schedule-label">{{ weekdayNames[today.today_schedule.weekday - 1] || '今天' }} · 计划安排</span><b>今天是计划休息日</b><p>这是当前周计划中的安排。</p>
        </template>
        <template v-else>
          <b>{{ today.today_schedule.status === 'legacy_plan' ? '本周计划尚无具体星期安排' : '本周还没有保存的计划' }}</b>
          <p>{{ today.today_schedule.status === 'legacy_plan' ? '旧计划没有记录训练星期，无法准确定位今天的会话。' : '可以前往周计划页，选择训练星期并生成计划。' }}</p>
          <button class="text-button" type="button" @click="router.push({ name: 'plan' })">前往周计划 →</button>
        </template>
      </div>
    </template>
    <p v-else-if="safety.errorMessage" role="alert">{{ safety.errorMessage }}</p>
  </article>
</template>
