<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import BaseDialog from '@/components/common/BaseDialog.vue'
import { useShapingStore } from '@/stores/shaping'
import { useNotice } from '@/composables/useNotice'
import { localDateString } from '@/utils/date'
import { CIRCUMFERENCES, SHAPE_METRICS, SHAPE_LABELS, SHAPE_RANGES, SOURCE_LABELS } from '@/constants/shaping'
import type { ShapeMeasurementPayload } from '@/api/types'
import FilterSelect from '@/components/ui/FilterSelect.vue'
const shaping = useShapingStore()
const notice = useNotice()
const dialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const form = reactive<ShapeMeasurementPayload>({ recorded_on: localDateString(), waist_cm: null, hip_cm: null, chest_cm: null, arm_cm: null, thigh_cm: null, body_fat_percent: null, skeletal_muscle_kg: null, composition_source: null })
const error = ref('')
const sourceValue = computed({ get: () => form.composition_source ?? '', set: (value: string) => { form.composition_source = value ? value as NonNullable<ShapeMeasurementPayload['composition_source']> : null } })
const sourceOptions = Object.entries(SOURCE_LABELS).map(([value, label]) => ({ value, label }))
function fill(date: string): void {
  const row = shaping.measurements.find(item => item.recorded_on === date)
  for (const metric of SHAPE_METRICS) form[metric] = row?.[metric] ?? null
  form.composition_source = row?.composition_source ?? null
  error.value = ''
}
watch(() => form.recorded_on, fill)
function open(date: string): void { form.recorded_on = date; fill(date); dialog.value?.open() }
async function save(): Promise<void> {
  error.value = ''
  const payload = { ...form }
  for (const metric of SHAPE_METRICS) {
    const value = form[metric]
    payload[metric] = value == null || String(value) === '' ? null : Number(value)
  }
  if (!SHAPE_METRICS.some(metric => payload[metric] != null)) { error.value = '请至少填写一项测量数据。'; return }
  if (payload.body_fat_percent == null && payload.skeletal_muscle_kg == null) payload.composition_source = null
  try {
    const message = await shaping.saveMeasurement(payload)
    dialog.value?.close()
    notice.notify(message, 'success')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '测量数据保存失败。' }
}
defineExpose({ open })
</script>

<template>
  <BaseDialog ref="dialog" class="user-dialog shape-measurement-dialog" aria-labelledby="shape-measure-title">
    <div class="user-dialog-top"><div><p class="eyebrow">MEASUREMENT</p><h2 id="shape-measure-title">记录身体变化</h2></div><button class="user-dialog-close" :disabled="shaping.saving" aria-label="关闭测量窗口" @click="dialog?.close()">×</button></div>
    <p class="shape-muted">只填写实际测过的数据，可留空。同一天保存会更新该日整份记录；清空的指标也会清除。体重在身体档案中单独记录。</p>
    <form class="form-stack" @submit.prevent="save">
      <label class="field"><span>测量日期</span><input v-model="form.recorded_on" type="date" :max="localDateString()" required :disabled="shaping.saving" /></label>
      <fieldset class="shape-form-fieldset" :disabled="shaping.saving"><legend>围度（厘米）</legend><div class="field-row"><label v-for="metric in CIRCUMFERENCES" :key="metric" class="field"><span>{{ SHAPE_LABELS[metric] }}</span><input v-model.number="form[metric]" type="number" step="0.1" :min="SHAPE_RANGES[metric][0]" :max="SHAPE_RANGES[metric][1]" placeholder="未测量可留空" /></label></div></fieldset>
      <fieldset class="shape-form-fieldset" :disabled="shaping.saving"><legend>体成分（实测，可选）</legend><div class="field-row"><label class="field"><span>体脂率（%）</span><input v-model.number="form.body_fat_percent" type="number" min="3" max="65" step="0.1" placeholder="填写设备或报告读数" /></label><label class="field"><span>骨骼肌量（kg）</span><input v-model.number="form.skeletal_muscle_kg" type="number" min="5" max="100" step="0.1" placeholder="确认是骨骼肌量" /></label></div><label class="field"><span>体成分来源</span><FilterSelect v-model="sourceValue" :options="sourceOptions" aria-label="体成分来源" :disabled="shaping.saving" placeholder="请选择数据来源" /></label></fieldset>
      <p v-if="error" class="shape-error" role="alert">{{ error }}</p>
      <div class="shape-actions"><button class="button button-quiet" type="button" :disabled="shaping.saving" @click="dialog?.close()">取消</button><button class="button button-primary" :disabled="shaping.saving">{{ shaping.saving ? '正在保存…' : '保存测量' }}</button></div>
    </form>
  </BaseDialog>
</template>
