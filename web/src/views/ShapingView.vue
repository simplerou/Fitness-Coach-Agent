<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { reportModule, moduleTitle } from '@/utils/moduleNavigation'
import PageHeader from '@/components/ui/PageHeader.vue'
import ShapeTrendDashboard from '@/components/shaping/ShapeTrendDashboard.vue'
import MeasurementDialog from '@/components/shaping/MeasurementDialog.vue'
import CircumferencePanel from '@/components/shaping/CircumferencePanel.vue'
import CompositionPanel from '@/components/shaping/CompositionPanel.vue'
import ShapeTargets from '@/components/shaping/ShapeTargets.vue'
import ShapePhotos from '@/components/shaping/ShapePhotos.vue'
import ShapeHistory from '@/components/shaping/ShapeHistory.vue'
import WeakPartPanel from '@/components/shaping/WeakPartPanel.vue'
import ShapeReportsPanel from '@/components/shaping/ShapeReportsPanel.vue'
import ReviewView from '@/views/ReviewView.vue'
import { useShapingStore } from '@/stores/shaping'
import { SHAPE_LABELS } from '@/constants/shaping'
import { localDateString } from '@/utils/date'

const shaping = useShapingStore()
const route = useRoute()
const router = useRouter()
const measurement = ref<InstanceType<typeof MeasurementDialog> | null>(null)
const tab = computed(() => reportModule(route.query))
const due = computed(() => shaping.reminders.filter((item) => item.due))
const dueNames = computed(() => due.value.map((item) => SHAPE_LABELS[item.metric]).join('、'))
async function reload() { try { await shaping.load() } catch { /* 错误在页面内展示 */ } }
watch(() => route.query.action, (action) => { if (action === 'record') measurement.value?.open(localDateString()) })
onMounted(async () => { await reload(); if (route.query.action === 'record') measurement.value?.open(localDateString()) })
</script>

<template>
  <section class="page active report-workspace">
    <PageHeader :title="moduleTitle(route)" :description="tab === 'trend' ? '查看体重与身体指标趋势，观察长期变化' : tab === 'measurements' ? '记录围度、体成分与对比照片，追踪身体变化' : '回顾本周训练、饮食与恢复情况，了解执行表现'">
      <template #actions><button v-if="tab === 'measurements'" class="button button-primary" :disabled="shaping.saving" @click="measurement?.open(localDateString())">记录测量</button><button class="button button-quiet" :disabled="shaping.loading" @click="reload">刷新</button></template>
    </PageHeader>
    <div v-if="shaping.error" class="error-state" role="alert"><span>{{ shaping.error }}</span><button class="button button-quiet" @click="reload">重试</button></div>
    <div v-else-if="shaping.loading && !shaping.data" class="loading-skeleton report-loading" />
    <template v-else-if="shaping.data">
      <template v-if="tab === 'trend'">
        <article class="expectation-strip"><b>变化通常在 4–8 周逐渐显现</b><span>个体差异很大，这不是效果承诺。体重、围度、体成分和线条可以不同步。</span></article>
        <ShapeTrendDashboard />
        <ShapeTargets />
      </template>
      <template v-else-if="tab === 'measurements'">
        <div class="measurement-reminder" :class="{ due: due.length }"><div><b>{{ due.length ? '到双周测量时间了' : '保持相同条件记录' }}</b><span>{{ due.length ? `${dueNames}已到复测日期。` : '每两周记录一次，比每天测量更容易看出趋势。' }}</span></div><button class="button button-quiet" @click="measurement?.open(localDateString())">去测量</button></div>
        <div class="measurement-grid"><CircumferencePanel @record="measurement?.open(localDateString())" /><CompositionPanel @record="measurement?.open(localDateString())" @weight="router.push({ name: 'profile' })" /></div>
        <ShapePhotos />
        <ShapeHistory @edit="(date) => measurement?.open(date)" />
      </template>
      <template v-else>
        <ReviewView embedded />
        <div class="report-insight-grid"><WeakPartPanel /><ShapeReportsPanel /></div>
      </template>
    </template>
    <MeasurementDialog ref="measurement" />
  </section>
</template>
