<script setup lang="ts">
import { onMounted, ref } from 'vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import DietDailyDashboard from '@/components/diet/DietDailyDashboard.vue'
import DietPlanResult from '@/components/diet/DietPlanResult.vue'
import DietPlanHistoryPanel from '@/components/diet/DietPlanHistoryPanel.vue'
import DietFoodLibraryDialog from '@/components/diet/DietFoodLibraryDialog.vue'
import { useDietStore } from '@/stores/diet'
import { useNotice } from '@/composables/useNotice'

const diet = useDietStore()
const notice = useNotice()
const consent = ref(false)
const activeModule = ref<'log' | 'records' | 'weekly'>('log')
const foodLibrary = ref<InstanceType<typeof DietFoodLibraryDialog> | null>(null)
const pageTitle = () => activeModule.value === 'log' ? '今日日志' : activeModule.value === 'records' ? '饮食规划记录' : '一周饮食计划'
onMounted(async () => {
  try { await diet.loadAll() } catch (error) { notice.notify(error instanceof Error ? error.message : '饮食记录暂时无法读取。', 'error') }
})
async function generate() {
  try {
    notice.notify(await diet.generatePlan(consent.value), 'success')
    activeModule.value = 'weekly'
  } catch (error) { notice.notify(error instanceof Error ? error.message : '暂时无法生成饮食规划。', 'error') }
}
</script>

<template>
  <section class="page active diet-workspace">
    <PageHeader title="饮食工作台" :breadcrumbs="['饮食', pageTitle()]" :description="activeModule === 'log' ? '按餐次记录并查看当日营养摄入' : activeModule === 'records' ? '查看已保存的规划快照，按需启动 AI 生成' : '查看当前或历史版本的一周餐次安排'">
      <template #actions>
        <template v-if="activeModule === 'log'">
          <label class="compact-date"><span>日期</span><input v-model="diet.selectedDate" type="date" @change="diet.loadSelectedDate" /></label>
          <button class="button button-quiet" @click="foodLibrary?.open()">搜索食物</button>
        </template>
      </template>
    </PageHeader>
    <nav class="secondary-tabs" aria-label="饮食模块">
      <button type="button" :class="{ active: activeModule === 'log' }" @click="activeModule = 'log'">今日日志</button>
      <button type="button" :class="{ active: activeModule === 'records' }" @click="activeModule = 'records'">饮食规划记录</button>
      <button type="button" :class="{ active: activeModule === 'weekly' }" @click="activeModule = 'weekly'">一周饮食计划</button>
    </nav>
    <div v-if="activeModule === 'log' && diet.loading" class="diet-workspace-grid"><div v-for="index in 3" :key="index" class="loading-skeleton" /></div>
    <DietDailyDashboard v-else-if="activeModule === 'log'" />
    <DietPlanHistoryPanel v-else-if="activeModule === 'records'" v-model:consent="consent" @generate="generate" @open-weekly="activeModule = 'weekly'" />
    <DietPlanResult v-else @open-profile="activeModule = 'records'" />
    <DietFoodLibraryDialog ref="foodLibrary" />
  </section>
</template>
