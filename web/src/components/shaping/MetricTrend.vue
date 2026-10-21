<script setup lang="ts">
import { computed } from 'vue'
import TrendChart from '@/components/charts/TrendChart.vue'
const props=defineProps<{label:string;unit:string;entries:{date:string;value:number}[]}>()
const recent=computed(()=>props.entries.slice(-12))
</script>
<template><div class="shape-trend"><TrendChart :labels="recent.map(item=>item.date)" :series="[{name:`${label} ${unit}`,data:recent.map(item=>item.value),colorToken:'--brand'}]" :height="220"/><p class="fine-print">{{recent.length===1?'已有首次记录，再测量一次就能比较变化。':'按实际日期展示最近 12 次读数；缺失日期不会被推断。'}}</p><details v-if="recent.length" class="shape-trend-values"><summary>查看具体读数</summary><ul><li v-for="entry in recent" :key="entry.date">{{entry.date}}·{{entry.value}} {{unit}}</li></ul></details></div></template>
