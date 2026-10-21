<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
const route = useRoute()
const router = useRouter()
const active = computed(() => route.name === 'review' ? 'review' : String(route.query.tab || 'trend'))
function go(tab: string) { void router.push(tab === 'review' ? { name: 'shaping', query: { tab: 'review' } } : { name: 'shaping', query: { tab } }) }
</script>
<template><nav class="secondary-tabs" aria-label="报告页面"><button :class="{ active: active === 'trend' }" @click="go('trend')">趋势</button><button :class="{ active: active === 'measurements' }" @click="go('measurements')">体测</button><button :class="{ active: active === 'review' }" @click="go('review')">周回顾</button></nav></template>
