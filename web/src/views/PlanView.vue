<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { shiftDate } from '@/utils/date'
import { usePlanStore } from '@/stores/plan'
import { useNotice } from '@/composables/useNotice'
import PlanSettingsForm from '@/components/plan/PlanSettingsForm.vue'
import PlanHistoryList from '@/components/plan/PlanHistoryList.vue'
import WeeklyPlanBoard from '@/components/plan/WeeklyPlanBoard.vue'
import TrainingTabs from '@/components/training/TrainingTabs.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'

const plan = usePlanStore()
const notice = useNotice()
const route = useRoute()
const showingHistory = computed(() => route.query.view === 'history')

onMounted(async () => {
  try { await plan.loadAll() }
  catch (error) { notice.notify(error instanceof Error ? error.message : '暂时无法读取训练计划。', 'error') }
})

async function generate(): Promise<void> {
  try { notice.notify(await plan.create(), 'success') }
  catch (error) { notice.notify(error instanceof Error ? error.message : '暂时无法生成训练计划。', 'error') }
}
</script>

<template>
  <section class="page active">
    <PageHeader :title="showingHistory ? '历史周计划' : '训练编排'" :breadcrumbs="showingHistory ? ['训练', '历史周计划'] : ['训练', '周计划']" />
    <TrainingTabs />
    <PlanHistoryList v-if="showingHistory" />
    <template v-else>
      <SectionCard title="本周安排" :subtitle="plan.currentWeekStart ? `${plan.currentWeekStart} 至 ${shiftDate(plan.currentWeekStart, 6)}` : '还没有生成计划'">
        <WeeklyPlanBoard />
      </SectionCard>
      <details class="workspace-details"><summary>计划偏好与生成设置</summary><PlanSettingsForm @generate="generate" /></details>
    </template>
    <article v-if="!showingHistory" class="panel plan-explanation-card workspace-note" aria-live="polite">
      <div class="panel-head"><div><p class="eyebrow">PLAN NOTES</p><h3>计划说明</h3></div><span class="tag">千问辅助编排</span></div>
      <div class="plan-explanation-content">
        <template v-if="plan.selectedPlan">
          <p class="explanation-lead">本周计划：围绕“{{ plan.selectedPlan.focus }}”安排，共 {{ plan.selectedPlan.days_per_week }} 天训练。以下内容根据本周当前计划整理。</p>
          <p class="profile-plan-note">本次计划读取了个人档案。身体数据用于进度对照；训练安排仍依据你选择的训练目标、经验、器械和时间，不会单凭 BMI 自动加量。</p>
          <div class="explanation-block"><h4>执行时可以留意</h4><ul><li>开始前先查看计划中的训练内容和动作说明，按自己能够控制的节奏进行。</li><li>计划是通用模板，不要求为了补上未完成的训练而临时加量。</li><li>如果训练中出现明显不适，请停止训练；症状严重、持续或加重时，及时寻求专业帮助。</li></ul></div>
          <p class="explanation-source">说明来源：项目配置的通义千问模型根据训练偏好和动作库候选编排；模型只选择动作库中的动作，不会接收账号标识或具体身体测量数值。</p>
        </template>
        <div v-else class="empty-state"><p>生成周计划后，这里会说明本周安排概况和通用执行提醒。</p></div>
      </div>
      <p class="fine-print">说明仅整理当前计划模板，不进行安全判断，也不是医疗或个体化处方。</p>
    </article>
  </section>
</template>
