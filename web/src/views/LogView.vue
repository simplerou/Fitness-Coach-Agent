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
import TrainingLogHistory from '@/components/training/TrainingLogHistory.vue'
import type { ExerciseEntryPayload, LogCompletion, RecoveryPayload, SkipReason } from '@/api/types'

const logs = useLogStore()
const training = useTrainingStore()
const review = useReviewStore()
const notice = useNotice()
const form = reactive<{ completion: LogCompletion; rpe: number | null; skip_reason: SkipReason | ''; note: string }>({ completion: 'completed', rpe: null, skip_reason: '', note: '' })
const exercises = ref<ExerciseEntryPayload[]>([])
const recoveryDialog = ref<InstanceType<typeof RecoveryCheckinDialog> | null>(null)
const saving = ref(false)
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
  <section class="page active">
    <div class="section-heading"><div><p class="eyebrow">TRAINING LOG</p><h2>练完，记一笔</h2></div><span class="tag">训练后记录</span></div>
    <RecoveryPanel :summary="training.recovery" />
    <div class="grid training-log-grid">
      <article class="panel"><div class="panel-head"><div><p class="eyebrow">SESSION</p><h3>记录本次训练</h3></div><span class="step-no">01</span></div>
        <form class="form-stack" @submit.prevent="submit">
          <label class="field"><span>训练日期</span><input v-model="logs.selectedDate" type="date" required /></label>
          <p class="log-plan-context" aria-live="polite">{{ contextText() }}</p>
          <label class="field"><span>完成情况</span><select v-model="form.completion"><option value="completed">按计划完成</option><option value="partial">部分完成</option><option value="skipped">未进行训练</option></select></label>
          <label class="field"><span>主观用力程度 RPE（1–10，可不填）</span><input v-model.number="form.rpe" type="number" min="1" max="10" placeholder="例如 6" /></label>
          <label v-if="form.completion === 'skipped'" class="field"><span>未完成原因</span><select v-model="form.skip_reason"><option value="">请选择</option><option value="no_time">没时间</option><option value="too_tired">太累</option><option value="discomfort">身体不适</option><option value="other">其他</option></select></label>
          <label class="field"><span>补充说明（可不填）</span><textarea v-model="form.note" rows="2" maxlength="240" placeholder="只填写你愿意记录的内容"></textarea></label>
          <ExerciseEntryEditor v-if="form.completion !== 'skipped'" v-model="exercises" />
          <button class="button button-primary" type="submit" :disabled="saving">{{ saving ? '正在保存…' : '下一步：恢复打卡' }}</button>
        </form>
      </article>
      <TrainingLogHistory @notice="notice.notify($event, 'success')" />
    </div>
    <RecoveryCheckinDialog ref="recoveryDialog" @confirm="save" />
  </section>
</template>
