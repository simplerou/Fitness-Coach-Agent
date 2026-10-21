<script setup lang="ts">
import { computed, ref } from 'vue'
import DataTable, { type TableColumn } from '@/components/ui/DataTable.vue'
import Drawer from '@/components/ui/Drawer.vue'
import AdviceCard from '@/components/ui/AdviceCard.vue'
import { useTrainingStore } from '@/stores/training'
import type { DetailedTrainingLog } from '@/api/types'
import { createLog } from '@/api/log'

const training = useTrainingStore()
const active = ref<DetailedTrainingLog | null>(null)
const batchOpen = ref(false)
const batchText = ref('')
const batchSaving = ref(false)
const batchResults = ref<Array<{ line: string; ok: boolean; message: string }>>([])
const columns: TableColumn[] = [
  { key: 'training_date', label: '日期' }, { key: 'title', label: '计划动作' }, { key: 'completion_label', label: '完成度' },
  { key: 'rpe_label', label: 'RPE' }, { key: 'weight', label: '主要重量' }, { key: 'note_label', label: '备注' },
]
const rows = computed(() => training.logs.map((item) => ({
  ...item,
  title: item.planned_session_title || item.exercises.map((row) => row.exercise_name).slice(0, 2).join('、') || '自主训练',
  completion_label: ({ completed: '已完成', partial: '部分完成', skipped: '未训练' })[item.completion],
  rpe_label: item.rpe ?? '未记录',
  weight: item.exercises.length ? `${Math.max(...item.exercises.map((row) => row.weight_kg))} kg` : '未记录',
  note_label: item.note || '未记录',
})))
function detail(row: Record<string, unknown>) { active.value = training.logs.find((item) => item.id === row.id) ?? null }
async function submitBatch() {
  const lines = batchText.value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  batchResults.value = []
  batchSaving.value = true
  for (const line of lines) {
    const [date, completionRaw, rpeRaw, ...noteParts] = line.split(',').map((item) => item.trim())
    const completion = completionRaw === 'partial' ? 'partial' : completionRaw === 'completed' ? 'completed' : null
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date || '') || !completion) { batchResults.value.push({ line, ok: false, message: '格式错误：完成度仅支持 completed / partial' }); continue }
    const rpe = rpeRaw ? Number(rpeRaw) : null
    try {
      await createLog({ training_date: date, completion, rpe: rpe != null && Number.isFinite(rpe) ? rpe : null, skip_reason: null, note: noteParts.join(',') || null })
      batchResults.value.push({ line, ok: true, message: '已保存' })
    } catch (error) { batchResults.value.push({ line, ok: false, message: error instanceof Error ? error.message : '保存失败' }) }
  }
  await training.load()
  batchSaving.value = false
}
</script>

<template>
  <details class="batch-entry" :open="batchOpen" @toggle="batchOpen = ($event.target as HTMLDetailsElement).open"><summary>批量录入</summary><p>每行格式：日期, completed/partial, RPE, 备注。后端会逐条保存并返回结果。</p><textarea v-model="batchText" rows="5" placeholder="2026-10-20,completed,7,上肢训练"/><button class="button button-primary" :disabled="batchSaving || !batchText.trim()" @click="submitBatch">{{ batchSaving ? '正在逐条保存…' : '提交批量记录' }}</button><ul v-if="batchResults.length"><li v-for="result in batchResults" :key="result.line" :class="{ success: result.ok, failure: !result.ok }"><b>{{ result.ok ? '成功' : '失败' }}</b><span>{{ result.line }}·{{ result.message }}</span></li></ul></details>
  <DataTable :columns="columns" :rows="rows" row-key="id" empty-text="本周还没有训练记录">
    <template #cell-completion_label="{ row, value }"><span class="table-status" :class="`is-${row.completion}`">{{ value }}</span></template>
    <template #actions="{ row }"><button class="text-button" @click="detail(row)">详情</button></template>
  </DataTable>
  <Drawer :open="Boolean(active)" title="训练记录详情" @close="active = null">
    <template v-if="active"><div class="record-detail-head"><h3>{{ active.training_date }}</h3><p>{{ active.planned_session_title || '自主训练' }} · RPE {{ active.rpe ?? '未记录' }}</p></div><div class="record-exercises"><article v-for="item in active.exercises" :key="item.id"><b>{{ item.exercise_name }}</b><span>{{ item.sets }} 组 × {{ item.reps }} 次 · {{ item.weight_kg }} kg · RPE {{ item.rpe }}</span></article></div><div v-if="active.recovery" class="record-recovery"><b>恢复状态</b><p>{{ active.recovery.message }}</p></div><AdviceCard v-for="advice in active.advice" :key="advice.id" :title="`${advice.exercise_name}·进阶建议`" :evidence="advice.reason" :impact="`${advice.prescription.sets} 组 × ${advice.prescription.reps} 次·${advice.prescription.weight_kg} kg`" :status="advice.status" @adopt="training.resolveAdvice(advice.id, 'adopted')" @ignore="training.resolveAdvice(advice.id, 'ignored')" @undo="training.undoAdvice(advice.id)" /></template>
  </Drawer>
</template>
