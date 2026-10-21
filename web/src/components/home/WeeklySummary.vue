<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useHomeStore } from '@/stores/home'
import { useReviewStore } from '@/stores/review'
const home = useHomeStore(); const review = useReviewStore(); const router = useRouter()
const summary = computed(() => review.result?.summary ?? null)
const report = computed(() => home.latestReport)
</script>
<template><div class="home-weekly-summary"><div v-if="summary"><span>本周进度</span><strong>已完成 {{ summary.completed_count }}/{{ summary.planned_elapsed_day_count || summary.planned_day_count }} 个计划训练日</strong><p>训练记录 {{ summary.session_count }} 次 · 饮食记录 {{ summary.diet_days_with_meals }} 天</p></div><div v-else><span>上周报告</span><strong>数据样本不足</strong><p>完成训练、饮食或围度记录后，这里会出现周期反馈。</p></div><button class="button button-quiet" @click="router.push({ name: report ? 'shaping' : 'review', query: report ? { section: 'reports' } : {} })">{{ report ? '查看周/月塑型报告' : '查看周回顾' }}</button></div></template>
