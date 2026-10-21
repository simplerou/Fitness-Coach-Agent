<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import BaseDialog from '@/components/common/BaseDialog.vue'
import { useShapingStore } from '@/stores/shaping'
import { useNotice } from '@/composables/useNotice'
import { CIRCUMFERENCES, SHAPE_LABELS, SHAPE_RANGES, SHAPE_UNITS } from '@/constants/shaping'
import type { ShapeTargetMetric } from '@/api/types'
import FilterSelect from '@/components/ui/FilterSelect.vue'
const shaping = useShapingStore()
const notice = useNotice()
const dialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const error = ref('')
const options: ShapeTargetMetric[] = [...CIRCUMFERENCES, 'body_fat_percent']
const form = reactive<{ metric: ShapeTargetMetric; value: number | null }>({ metric: 'waist_cm', value: null })
const current = computed(() => shaping.latest(form.metric))
const metricValue = computed({ get: () => form.metric, set: (value: string) => { form.metric = value as ShapeTargetMetric; form.value = shaping.data?.targets.find(target => target.metric === form.metric)?.target_value ?? null; error.value = '' } })
const metricOptions = options.map(metric => ({ value: metric, label: SHAPE_LABELS[metric] }))
function open(metric: ShapeTargetMetric = 'waist_cm'): void {
  form.metric = metric
  form.value = shaping.data?.targets.find(target => target.metric === metric)?.target_value ?? null
  error.value = ''
  dialog.value?.open()
}
async function save(): Promise<void> {
  if (form.value == null || String(form.value) === '') return
  try {
    const message = await shaping.saveTarget(form.metric, Number(form.value))
    dialog.value?.close()
    notice.notify(message, 'success')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '目标保存失败。' }
}
async function clear(): Promise<void> {
  try {
    const message = await shaping.removeTarget(form.metric)
    dialog.value?.close()
    notice.notify(message, 'success')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '目标清除失败。' }
}
</script>

<template>
  <article class="panel shape-panel">
    <div class="panel-head"><div><p class="eyebrow">SMALL STEPS, REAL PROGRESS</p><h3>目标与里程碑</h3></div><button class="text-button" :disabled="shaping.saving" @click="open()">设置目标</button></div>
    <p v-if="!shaping.data?.targets.length" class="shape-muted">先记录一次围度或体脂率，再选一个你想追踪的目标。目标可以增加或减少，不必把每个指标都设成越低越好。</p>
    <div class="shape-targets">
      <section v-for="target in shaping.data?.targets" :key="target.metric" class="shape-target-card">
        <div class="shape-target-head"><b>{{ SHAPE_LABELS[target.metric] }}</b><button class="text-button" :disabled="shaping.saving" @click="open(target.metric)">调整</button></div>
        <p><strong>{{ target.current_value ?? '未记录' }}</strong> <small>{{ SHAPE_UNITS[target.metric] }}</small><span> → 目标 {{ target.target_value }} {{ SHAPE_UNITS[target.metric] }}</span></p>
        <div class="shape-progress" role="progressbar" :aria-label="`${SHAPE_LABELS[target.metric]}目标进度`" :aria-valuenow="target.progress_percent ?? undefined" aria-valuemin="0" aria-valuemax="100"><span :style="{ width: `${target.progress_percent ?? 0}%` }" /></div>
        <div class="shape-target-progress"><span>{{ target.progress_percent == null ? '等待测量' : `${target.progress_percent}%` }}</span><small>起点 {{ target.baseline_value }} · {{ target.baseline_date }}</small></div>
        <p class="fine-print">当前读数日期：{{ target.current_date ?? '未记录' }}；进度按起点到目标的距离计算。</p>
        <div class="shape-milestones"><span v-for="step in [25, 50, 75, 100]" :key="step" :class="{ earned: target.milestones.includes(step) }">{{ step }}%{{ target.milestones.includes(step) ? '·已达成' : '' }}</span></div>
      </section>
    </div>
    <p class="fine-print">已解锁节点会保留，当前进度随实际读数变化；修改目标会以最新测量值重新起算。目标不自动改变训练强度或饮食热量。</p>
    <BaseDialog ref="dialog" class="user-dialog" aria-labelledby="shape-target-title"><div class="user-dialog-top"><h2 id="shape-target-title">设置塑型目标</h2><button class="user-dialog-close" :disabled="shaping.saving" aria-label="关闭目标设置" @click="dialog?.close()">×</button></div>
      <form class="form-stack" @submit.prevent="save"><label class="field"><span>追踪指标</span><FilterSelect v-model="metricValue" :options="metricOptions" aria-label="追踪指标" :disabled="shaping.saving" /></label><p class="shape-muted">{{ current ? `当前值 ${current[form.metric]} ${SHAPE_UNITS[form.metric]}，测于 ${current.recorded_on}` : '请先在“记录测量”中填写该指标。' }}</p><label class="field"><span>目标值（{{ SHAPE_UNITS[form.metric] }}）</span><input v-model.number="form.value" type="number" :min="SHAPE_RANGES[form.metric][0]" :max="SHAPE_RANGES[form.metric][1]" step="0.1" required :disabled="shaping.saving" placeholder="填写自己的参考目标" /></label><p class="fine-print">体脂率使用设备或报告读数，不从 BMI 推算。生长发育期不建议自行设置减脂目标；疾病、孕期或特殊营养需求请先咨询专业人员。</p><p v-if="error" class="shape-error" role="alert">{{ error }}</p><div class="shape-actions"><button v-if="shaping.data?.targets.some(target => target.metric === form.metric)" class="button button-quiet" type="button" :disabled="shaping.saving" @click="clear">清除目标</button><button class="button button-primary" :disabled="!current || shaping.saving">{{ shaping.saving ? '正在保存…' : '保存目标' }}</button></div></form>
    </BaseDialog>
  </article>
</template>
