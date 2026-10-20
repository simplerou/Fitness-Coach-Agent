<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useShapingStore } from '@/stores/shaping'
import { useRouter } from 'vue-router'
import MeasurementDialog from '@/components/shaping/MeasurementDialog.vue'
import CircumferencePanel from '@/components/shaping/CircumferencePanel.vue'
import CompositionPanel from '@/components/shaping/CompositionPanel.vue'
import ShapeTargets from '@/components/shaping/ShapeTargets.vue'
import ShapePhotos from '@/components/shaping/ShapePhotos.vue'
import ShapeHistory from '@/components/shaping/ShapeHistory.vue'
import { SHAPE_LABELS } from '@/constants/shaping'
import { localDateString } from '@/utils/date'

const shaping = useShapingStore()
const router = useRouter()
const measurement = ref<InstanceType<typeof MeasurementDialog> | null>(null)
const due = computed(() => shaping.reminders.filter(row => row.due))
const dueNames = computed(() => due.value.map(row => SHAPE_LABELS[row.metric]).join('、'))
const nextDue = computed(() => shaping.data?.reminders.map(row => row.next_due_on).filter((date): date is string => date != null).sort()[0])
async function reload(): Promise<void> { try { await shaping.load() } catch { /* inline error with retry */ } }
onMounted(reload)
</script>

<template>
  <section class="page active shape-page">
    <div class="section-heading"><div><p class="eyebrow">SHAPE JOURNEY</p><h2>看见身体的变化</h2></div><button class="button button-primary" :disabled="!shaping.data || shaping.saving" @click="measurement?.open(localDateString())">记录测量</button></div>
    <article class="shape-expectation"><span class="shape-expectation-icon" aria-hidden="true">↗</span><div><b>给变化一点时间</b><p>变化通常在 4–8 周逐渐显现，个体差异很大，这不是效果承诺。体重、围度、体成分和线条可以不同步，用同条件的记录看趋势。</p></div></article>
    <div v-if="shaping.error" class="shape-error" role="alert">{{ shaping.error }} <button class="text-button" @click="reload">重新加载</button></div>
    <p v-if="shaping.loading && !shaping.data" role="status">正在读取塑型记录…</p>
    <template v-if="shaping.data">
      <div class="shape-reminder" :class="{ 'is-due': due.length }" role="status">
        <div><b>{{ due.length ? '到双周测量时间了' : shaping.measurements.length ? '每两周，留下一次可比的记录' : '从第一次测量开始' }}</b><p>{{ due.length ? `${dueNames}已到复测日期。` : nextDue ? `下次围度复测：${nextDue}。未填写的指标可随时补充。` : '先记录围度，之后会按每个部位的最近测量日期，在应用内提醒复测。' }}</p></div>
        <button class="button button-quiet" :disabled="shaping.saving" @click="measurement?.open(localDateString())">{{ due.length ? '去复测' : '记录围度 / 体成分' }}</button>
      </div>
      <CircumferencePanel @record="measurement?.open(localDateString())" />
      <CompositionPanel @record="measurement?.open(localDateString())" @weight="router.push({ name: 'profile' })" />
      <ShapeTargets />
      <ShapePhotos />
      <ShapeHistory @edit="date => measurement?.open(date)" />
      <div class="shape-flow-links"><span>让行动与变化连起来</span><button class="text-button" @click="router.push({ name: 'plan' })">查看训练计划 →</button><button class="text-button" @click="router.push({ name: 'diet' })">查看饮食规划 →</button></div>
    </template>
    <MeasurementDialog ref="measurement" />
  </section>
</template>
