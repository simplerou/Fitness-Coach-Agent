<script setup lang="ts">
import { onMounted } from 'vue'
import TodayActions from '@/components/home/TodayActions.vue'
import QuickRecords from '@/components/home/QuickRecords.vue'
import SmartRecommendations from '@/components/home/SmartRecommendations.vue'
import WeeklySummary from '@/components/home/WeeklySummary.vue'
import OverviewStats from '@/components/dashboard/OverviewStats.vue'
import OverviewCharts from '@/components/dashboard/OverviewCharts.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import { useHomeStore } from '@/stores/home'

const home = useHomeStore()
onMounted(() => void home.load())
</script>

<template>
  <section class="page active overview-page">
    <PageHeader title="今日概览" description="今天的行动、摄入和长期变化">
      <template #actions><button class="button button-quiet" :disabled="home.loading" @click="home.load">刷新数据</button></template>
    </PageHeader>
    <div v-if="home.loading" class="overview-stat-grid" aria-label="正在加载"><div v-for="index in 4" :key="index" class="loading-skeleton" /></div>
    <template v-else>
      <div v-if="home.errors.length" class="overview-error" role="alert"><span>部分数据暂时无法更新，已展示可用内容。</span><button class="text-button" @click="home.load">重试</button></div>
      <OverviewStats />
      <OverviewCharts />
      <div class="overview-lower-grid">
        <SectionCard title="智能建议" subtitle="每天最多展示 2 条有记录依据的建议"><SmartRecommendations /></SectionCard>
        <SectionCard title="今日安排" subtitle="训练与饮食建议"><TodayActions /></SectionCard>
      </div>
      <div class="overview-bottom-grid"><SectionCard title="快捷记录"><QuickRecords /></SectionCard><SectionCard title="上周反馈"><WeeklySummary /></SectionCard></div>
    </template>
  </section>
</template>
