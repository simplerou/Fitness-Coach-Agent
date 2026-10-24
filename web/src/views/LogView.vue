<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useLogStore } from '@/stores/log'
import { useTrainingStore } from '@/stores/training'
import { useNotice } from '@/composables/useNotice'
import { useReviewStore } from '@/stores/review'
import { localDateString } from '@/utils/date'
import { createSmartTrainingLog } from '@/api/training'
import ExerciseEntryEditor from '@/components/training/ExerciseEntryEditor.vue'
import RecoveryCheckinDialog from '@/components/training/RecoveryCheckinDialog.vue'
import RecoveryPanel from '@/components/training/RecoveryPanel.vue'
import type { ExerciseEntryPayload, LogCompletion, RecoveryPayload, SkipReason } from '@/api/types'
import TrainingRecordsTable from '@/components/training/TrainingRecordsTable.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import FilterSelect from '@/components/ui/FilterSelect.vue'

const logs = useLogStore()
const training = useTrainingStore()
const review = useReviewStore()
const notice = useNotice()
const form = reactive<{ completion: LogCompletion; rpe: number | null; skip_reason: SkipReason | ''; note: string }>({ completion: 'completed', rpe: null, skip_reason: '', note: '' })
const exercises = ref<ExerciseEntryPayload[]>([])
const recoveryDialog = ref<InstanceType<typeof RecoveryCheckinDialog> | null>(null)
const saving = ref(false)
const completionOptions = [{ value: 'completed', label: '按计划完成' }, { value: 'partial', label: '部分完成' }, { value: 'skipped', label: '未进行训练' }]
const skipReasonOptions = [{ value: '', label: '请选择' }, { value: 'no_time', label: '没时间' }, { value: 'too_tired', label: '太累' }, { value: 'discomfort', label: '身体不适' }, { value: 'other', label: '其他' }]
function setCompletion(value: string): void { form.completion = value as LogCompletion }
function setSkipReason(value: string): void { form.skip_reason = value as SkipReason | '' }
const contextText = () => {
  const context = logs.sessionContext
  if (!context) return logs.error || '选择日期后查看对应的周计划安排。'
  if (context.status === 'training') return `对应计划训练：${context.session?.title || ''}。保存后会关联到这一天的计划。`
  if (context.status === 'rest') return '这一天是计划休息日；如果有额外训练，也可以照常记录。'
  if (context.status === 'before_registration') return '日期早于账号注册日，不能记录。'
  return '这一天没有可关联的周计划；保存的训练记录仍会正常保留。'
}

onMounted(() => { void logs.loadContext(); void training.loadExercises(); void training.load() })
watch(() => logs.selectedDate, () => { void logs.loadContext() })

function submit(): void {
  if (form.completion === 'skipped' && !form.skip_reason) { notice.notify('未完成训练时，请选择未完成原因。', 'error'); return }
  if (form.completion !== 'skipped' && !exercises.value.length) { notice.notify('请至少添加一个训练动作。', 'error'); return }
  recoveryDialog.value?.open()
}

async function save(recovery: RecoveryPayload): Promise<void> {
  saving.value = true
  try {
    const result = await createSmartTrainingLog({
      training_date: logs.selectedDate,
      completion: form.completion,
      rpe: form.rpe == null ? null : Number(form.rpe),
      skip_reason: form.skip_reason || null,
      note: form.note.trim() || null,
      exercises: form.completion === 'skipped' ? [] : exercises.value,
      recovery,
    })
    notice.notify(result.advice.length ? `${result.message} 已生成 ${result.advice.length} 条进阶建议。` : result.message, 'success')
    logs.selectedDate = localDateString()
    form.completion = 'completed'; form.rpe = null; form.skip_reason = ''; form.note = ''
    exercises.value = []
    await logs.loadContext()
    await training.load()
    void review.load()
  } catch (error) { notice.notify(error instanceof Error ? error.message : '训练记录保存失败。', 'error') }
  finally { saving.value = false }
}
</script>

<template>
  <section class="page active training-workspace">
    <PageHeader title="训练记录" description="记录每日训练与动作完成情况，回顾训练表现" />
    <RecoveryPanel :summary="training.recovery" />
    <div class="training-record-layout">
      <SectionCard title="记录本次训练" subtitle="保存后会生成恢复与进阶建议">
        <form class="form-stack" @submit.prevent="submit">
          <label class="field"><span>训练日期</span><input v-model="logs.selectedDate" type="date" required /></label>
          <p class="log-plan-context" aria-live="polite">{{ contextText() }}</p>
          <label class="field"><span>完成情况</span><FilterSelect :model-value="form.completion" :options="completionOptions" aria-label="完成情况" @update:model-value="setCompletion" /></label>
          <label class="field"><span>主观用力程度 RPE（1–10，可不填）</span><input v-model.number="form.rpe" type="number" min="1" max="10" placeholder="例如 6" /></label>
          <label v-if="form.completion === 'skipped'" class="field"><span>未完成原因</span><FilterSelect :model-value="form.skip_reason" :options="skipReasonOptions" aria-label="未完成原因" @update:model-value="setSkipReason" /></label>
          <label class="field"><span>补充说明（可不填）</span><textarea v-model="form.note" rows="2" maxlength="240" placeholder="只填写你愿意记录的内容"></textarea></label>
          <ExerciseEntryEditor v-if="form.completion !== 'skipped'" v-model="exercises" />
          <button class="button button-primary" type="submit" :disabled="saving">{{ saving ? '正在保存…' : '下一步：恢复打卡' }}</button>
        </form>
      </SectionCard>
      <SectionCard title="最近记录" subtitle="双击只读数据不会覆盖原记录"><TrainingRecordsTable /></SectionCard>
    </div>
    <RecoveryCheckinDialog ref="recoveryDialog" @confirm="save" />
  </section>
</template>
