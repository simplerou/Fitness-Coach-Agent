<script setup lang="ts">
import { onMounted } from 'vue'
import { usePlanStore } from '@/stores/plan'
import { useNotice } from '@/composables/useNotice'
import PlanSettingsForm from '@/components/plan/PlanSettingsForm.vue'
import PlanDisplay from '@/components/plan/PlanDisplay.vue'
import PlanHistoryList from '@/components/plan/PlanHistoryList.vue'
import ExerciseLibrary from '@/components/training/ExerciseLibrary.vue'

const plan = usePlanStore()
const notice = useNotice()

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
    <div class="section-heading"><div><p class="eyebrow">WEEKLY PLAN</p><h2>搭一份基础计划</h2></div><span class="tag">模板生成 · 可随时调整</span></div>
    <PlanSettingsForm @generate="generate" />
    <div class="grid two-col">
      <PlanDisplay />
      <PlanHistoryList />
    </div>
    <article class="panel plan-exercise-library"><div class="panel-head"><div><p class="eyebrow">EXERCISE LIBRARY</p><h3>选择动作前先看示范要领</h3></div><span class="tag">胸 / 背 / 腿 / 肩 / 臂 / 核心</span></div><p class="fine-print">按动作名称或目标肌群搜索；训练记录时可从同一动作库添加动作。</p><ExerciseLibrary /></article>
    <article class="panel plan-explanation-card" aria-live="polite">
      <div class="panel-head"><div><p class="eyebrow">PLAN NOTES</p><h3>计划说明</h3></div><span class="tag">本地模板</span></div>
      <div class="plan-explanation-content">
        <template v-if="plan.selectedPlan">
          <p class="explanation-lead">{{ plan.selectedIsHistorical ? `${plan.selectedWeek} 的计划：` : '本周计划：' }}围绕“{{ plan.selectedPlan.focus }}”安排，共 {{ plan.selectedPlan.days_per_week }} 天训练。{{ plan.selectedIsHistorical ? '这是已保存的历史计划，仅供回看，不代表本周训练建议。' : '以下内容根据本周当前计划整理。' }}</p>
          <p class="profile-plan-note">本次计划读取了个人档案。身体数据用于进度对照；训练安排仍依据你选择的训练目标、经验、器械和时间，不会单凭 BMI 自动加量。</p>
          <div class="explanation-block"><h4>执行时可以留意</h4><ul><li>开始前先查看计划中的训练内容和动作说明，按自己能够控制的节奏进行。</li><li>计划是通用模板，不要求为了补上未完成的训练而临时加量。</li><li>如果训练中出现明显不适，请停止训练；症状严重、持续或加重时，及时寻求专业帮助。</li></ul></div>
          <p class="explanation-source">说明来源：本地固定模板；未发送到外部模型服务。</p>
        </template>
        <div v-else class="empty-state"><p>生成周计划后，这里会说明本周安排概况和通用执行提醒。你也可以从历史列表选择已保存计划回看。</p></div>
      </div>
      <p class="fine-print">说明仅整理当前计划模板，不进行安全判断，也不是医疗或个体化处方。</p>
    </article>
  </section>
</template>
