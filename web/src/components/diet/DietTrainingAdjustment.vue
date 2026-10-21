<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useDietStore } from '@/stores/diet'
import { useShapingIntelligenceStore } from '@/stores/shapingIntelligence'
import { useNotice } from '@/composables/useNotice'
import AdviceCard from '@/components/ui/AdviceCard.vue'

const diet = useDietStore()
const intelligence = useShapingIntelligenceStore()
const notice = useNotice()
const dayLabels = { training: '训练日', rest: '休息日', recovery: '恢复日' }
async function load(): Promise<void> {
  try { await intelligence.loadDietAdjustment(diet.selectedDate) }
  catch (error) { notice.notify(error instanceof Error ? error.message : '饮食联动建议暂时无法读取。', 'error') }
}
async function decide(decision: 'adopted' | 'ignored'): Promise<void> {
  try { notice.notify(await intelligence.decideDiet(diet.selectedDate, decision), 'success') }
  catch (error) { notice.notify(error instanceof Error ? error.message : '联动建议处理失败。', 'error') }
}
watch(() => diet.selectedDate, load)
onMounted(load)
</script>

<template>
  <article class="panel diet-training-adjustment">
    <div class="panel-head"><div><p class="eyebrow">TRAINING × NUTRITION</p><h3>训练与饮食联动</h3></div><button class="text-button" @click="load">重新计算</button></div>
    <template v-if="intelligence.dietAdjustment?.suggestion">
      <div class="diet-adjustment-summary"><span class="tag">{{ dayLabels[intelligence.dietAdjustment.day_type || 'rest'] }}</span><b>{{ intelligence.dietAdjustment.status === 'adopted' ? '已采纳为当天目标' : '当天建议值' }}</b></div>
      <div class="diet-metrics"><div class="diet-metric">热量 <strong>{{ intelligence.dietAdjustment.suggestion.calories_kcal }}</strong> kcal</div><div class="diet-metric">蛋白质 <strong>{{ intelligence.dietAdjustment.suggestion.protein_g }}</strong> g</div><div class="diet-metric">碳水 <strong>{{ intelligence.dietAdjustment.suggestion.carbs_g }}</strong> g</div><div class="diet-metric">脂肪 <strong>{{ intelligence.dietAdjustment.suggestion.fat_g }}</strong> g</div></div>
      <AdviceCard title="今日营养目标调整" :evidence="intelligence.dietAdjustment.suggestion.reason" :impact="`热量 ${intelligence.dietAdjustment.suggestion.calories_kcal} kcal·蛋白质 ${intelligence.dietAdjustment.suggestion.protein_g} g·碳水 ${intelligence.dietAdjustment.suggestion.carbs_g} g·脂肪 ${intelligence.dietAdjustment.suggestion.fat_g} g`" :status="intelligence.dietAdjustment.status === 'adopted' ? 'adopted' : intelligence.dietAdjustment.status === 'ignored' ? 'ignored' : 'pending'" :undoable="false" @adopt="decide('adopted')" @ignore="decide('ignored')" />
      <details><summary>查看计算依据</summary><p>{{ intelligence.dietAdjustment.suggestion.calculation }}</p></details>
      <p class="fine-print">采纳只保存 {{ diet.selectedDate }} 的参考目标，不修改长期饮食档案。</p>
    </template>
    <p v-else class="shape-muted">{{ intelligence.dietAdjustment?.message || '正在读取基础饮食目标与训练安排…' }} {{ intelligence.dietAdjustment?.missing?.join('、') }}</p>
  </article>
</template>
