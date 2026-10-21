<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
const route = useRoute()
const router = useRouter()
</script>
<template>
  <nav class="secondary-tabs" aria-label="训练页面">
    <button :class="{ active: route.name === 'plan' && route.query.view !== 'history' }" @click="router.push({ name: 'plan' })">周计划</button>
    <button :class="{ active: route.name === 'plan' && route.query.view === 'history' }" @click="router.push({ name: 'plan', query: { view: 'history' } })">历史周计划</button>
    <button :class="{ active: route.name === 'log' }" @click="router.push({ name: 'log' })">训练记录</button>
  </nav>
</template>
