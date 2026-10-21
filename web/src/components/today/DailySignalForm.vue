<script setup lang="ts">
import { reactive } from 'vue'
import { useSafetyStore } from '@/stores/safety'
import { useNotice } from '@/composables/useNotice'
import type { Readiness } from '@/api/types'

const safety = useSafetyStore()
const notice = useNotice()
const form = reactive<{ readiness: Readiness | ''; sleep_hours: string; resting_hr: string }>({ readiness: '', sleep_hours: '', resting_hr: '' })

async function submit(): Promise<void> {
  if (!form.readiness) {
    notice.notify('请选择今天的主观状态。', 'error')
    return
  }
  try {
    await safety.saveSignal({
      readiness: form.readiness,
      sleep_hours: form.sleep_hours === '' ? null : Number(form.sleep_hours),
      resting_hr: form.resting_hr === '' ? null : Number(form.resting_hr),
    })
    notice.notify('状态已保存。', 'success')
  } catch (error) {
    notice.notify(error instanceof Error ? error.message : '请求失败，请稍后重试。', 'error')
  }
}
</script>

<template>
  <article class="panel">
    <div class="panel-head"><div><p class="eyebrow">CHECK-IN</p><h3>{{ safety.isRestDay ? '今天是计划休息日' : '记录今天的状态' }}</h3></div><span class="step-no">01</span></div>
    <form v-if="!safety.isRestDay" class="form-stack" @submit.prevent="submit">
      <fieldset><legend>主观状态</legend>
        <label class="choice"><input v-model="form.readiness" type="radio" name="readiness" value="good" required /><span><b>状态不错</b><small>精力和平时差不多或更好</small></span></label>
        <label class="choice"><input v-model="form.readiness" type="radio" name="readiness" value="okay" /><span><b>一般</b><small>不确定，或比平时略累</small></span></label>
        <label class="choice"><input v-model="form.readiness" type="radio" name="readiness" value="poor" /><span><b>状态较差</b><small>明显疲惫、恢复不足</small></span></label>
      </fieldset>
      <div class="field-row">
        <label class="field"><span>昨晚睡眠（小时，可不填）</span><input v-model="form.sleep_hours" type="number" min="0" max="24" step="0.25" placeholder="例如 7.5" /></label>
        <label class="field"><span>静息心率（可不填）</span><input v-model="form.resting_hr" type="number" min="25" max="240" placeholder="例如 62" /></label>
      </div>
      <button class="button button-primary" type="submit" :disabled="safety.submittingSignal">{{ safety.submittingSignal ? '正在保存…' : '保存状态' }}</button>
    </form>
    <p v-else-if="safety.isRestDay" class="fine-print">今天是计划休息日，无需填写训练状态。</p>
  </article>
</template>
