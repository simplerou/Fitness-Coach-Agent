<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { decidePlanAdjustment, previewPlanAdjustment } from '@/api/training'
import { useNotice } from '@/composables/useNotice'
import { usePlanStore } from '@/stores/plan'
import type { PlanAdjustment } from '@/api/types'

const props = defineProps<{ weekOf: string }>()
const notice = useNotice()
const plan = usePlanStore()
const preview = ref<PlanAdjustment | null>(null)
const loading = ref(false)
const kindLabels: Record<string, string> = { maintain: '保持计划', slight_increase: '小幅进阶', reduce: '降低负担', deload: '减载周', variation: '动作变式', hold: '暂停加量' }
async function generate(): Promise<void> {
  loading.value = true
  try { preview.value = await previewPlanAdjustment(props.weekOf) }
  catch (error) { notice.notify(error instanceof Error ? error.message : '无法生成下周调整预览。', 'error') }
  finally { loading.value = false }
}
async function decide(decision: 'adopted' | 'ignored'): Promise<void> {
  if (!preview.value) return
  try {
    const result = await decidePlanAdjustment(preview.value.id, decision)
    preview.value.status = decision
    if (decision === 'adopted') await Promise.all([plan.loadCurrent(), plan.loadHistory()])
    notice.notify(result.message, decision === 'adopted' ? 'success' : 'info')
  } catch (error) { notice.notify(error instanceof Error ? error.message : '计划调整操作失败。', 'error') }
}
onMounted(() => {
  if (new Date().getDay() === 0) void generate()
})
</script>

<template>
  <article class="panel plan-adjustment-panel"><div class="panel-head"><div><p class="eyebrow">NEXT WEEK</p><h3>下周计划调整预览</h3></div><button class="button button-primary" type="button" :disabled="loading" @click="generate">{{ loading ? '正在分析…' : '生成调整建议' }}</button></div>
    <p v-if="!preview" class="fine-print">结合完成率、平均 RPE、恢复状态和动作进阶情况生成预览。生成后不会自动修改计划。</p>
    <div v-else class="adjustment-preview">
      <div class="adjustment-title"><span class="tag">{{ kindLabels[preview.recommendation.kind] || preview.recommendation.kind }}</span><b>{{ preview.target_week_start }} 起执行</b></div>
      <section><h4>改了哪些</h4><ul><li v-for="item in preview.recommendation.changed" :key="item">{{ item }}</li></ul></section>
      <section><h4>为什么改</h4><ul><li v-for="item in preview.recommendation.reasons" :key="item">{{ item }}</li></ul></section>
      <section><h4>哪些不变</h4><ul><li v-for="item in preview.recommendation.unchanged" :key="item">{{ item }}</li></ul></section>
      <div v-if="preview.status === 'pending'" class="advice-actions"><button class="button button-primary" type="button" @click="decide('adopted')">确认并写入下周计划</button><button class="button button-quiet" type="button" @click="decide('ignored')">取消本次调整</button></div>
      <p v-else class="fine-print">{{ preview.status === 'adopted' ? '已确认并写入下周计划。' : '已取消本次调整。' }}</p>
    </div>
  </article>
</template>
