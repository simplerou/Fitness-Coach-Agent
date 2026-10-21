<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import VChart from 'vue-echarts'
import { use, type EChartsCoreOption } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart, HeatmapChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, MarkLineComponent, CalendarComponent, VisualMapComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, BarChart, PieChart, HeatmapChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, MarkLineComponent, CalendarComponent, VisualMapComponent])
const props = withDefaults(defineProps<{ option: EChartsCoreOption; height?: number | string; empty?: boolean; emptyText?: string }>(), { height: 280, empty: false, emptyText: '暂无可展示的数据' })
const emit = defineEmits<{ click: [params: unknown] }>()
const chart = ref<InstanceType<typeof VChart> | null>(null)
const style = computed(() => ({ height: typeof props.height === 'number' ? `${props.height}px` : props.height }))
onBeforeUnmount(() => chart.value?.dispose())
</script>
<template><div class="chart-shell" :style="style"><VChart v-if="!empty" ref="chart" class="chart-instance" :option="option" autoresize @click="emit('click',$event)"/><div v-else class="chart-empty"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19V9m5 10V5m5 14v-7m5 7H2"/></svg><span>{{emptyText}}</span></div></div></template>
