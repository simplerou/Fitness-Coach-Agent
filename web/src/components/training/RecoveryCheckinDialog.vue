<script setup lang="ts">
import { reactive, ref } from 'vue'
import BaseDialog from '@/components/common/BaseDialog.vue'
import type { RecoveryPayload } from '@/api/types'

const emit = defineEmits<{ confirm: [value: RecoveryPayload] }>()
const dialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const form = reactive<RecoveryPayload>({ soreness: 2, sleep_hours: 7, sleep_quality: 3, energy: 3, is_sick: false, warning_symptom: 'none', note: null })
function open(): void { dialog.value?.open() }
function submit(): void { emit('confirm', { ...form, note: form.note?.trim() || null }); dialog.value?.close() }
defineExpose({ open })
</script>

<template>
  <BaseDialog ref="dialog" class="user-dialog recovery-dialog">
    <form class="dialog-card form-stack" @submit.prevent="submit">
      <div class="user-dialog-top"><div><p class="eyebrow">RECOVERY CHECK-IN</p><h2>训练后恢复打卡</h2></div><button class="dialog-close" type="button" aria-label="关闭恢复打卡" @click="dialog?.close()">×</button></div>
      <p class="fine-print">用于判断是否需要保持、减量或休息，不作医疗诊断。</p>
      <div class="field-row"><label class="field"><span>肌肉酸痛度（1–5）</span><input v-model.number="form.soreness" type="number" min="1" max="5" required /></label><label class="field"><span>睡眠时长（小时）</span><input v-model.number="form.sleep_hours" type="number" min="0" max="24" step="0.5" required /></label></div>
      <div class="field-row"><label class="field"><span>睡眠质量（1–5）</span><input v-model.number="form.sleep_quality" type="number" min="1" max="5" required /></label><label class="field"><span>精神状态（1–5）</span><input v-model.number="form.energy" type="number" min="1" max="5" required /></label></div>
      <label class="field"><span>疼痛或肿胀信号</span><select v-model="form.warning_symptom"><option value="none">没有</option><option value="joint_pain">关节疼痛</option><option value="sharp_pain">锐痛</option><option value="swelling">肿胀</option></select></label>
      <label class="check-row"><input v-model="form.is_sick" type="checkbox" /><span>今天生病或明显不适</span></label>
      <label class="field"><span>备注（可选）</span><textarea v-model="form.note" maxlength="300" rows="2"></textarea></label>
      <div v-if="form.warning_symptom !== 'none'" class="recovery-warning">保存后不会生成训练进阶建议。请停止引发不适的动作并休息；若症状明显、持续或加重，请及时寻求专业医疗帮助。</div>
      <button class="button button-primary" type="submit">保存恢复打卡与训练记录</button>
    </form>
  </BaseDialog>
</template>
