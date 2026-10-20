<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

const router = useRouter()
const route = useRoute()
const tabs = [
  { name: 'today', label: '今日' },
  { name: 'plan', label: '周计划' },
  { name: 'log', label: '训练记录' },
  { name: 'diet', label: '饮食记录' },
  { name: 'shaping', label: '塑型追踪' },
  { name: 'review', label: '周回顾' },
]
</script>

<template>
  <nav class="tabs" aria-label="主要功能">
    <button
      v-for="tab in tabs"
      :key="tab.name"
      class="tab"
      :class="{ active: route.name === tab.name }"
      :aria-current="route.name === tab.name ? 'page' : undefined"
      type="button"
      @click="router.push({ name: tab.name })"
    >
      {{ tab.label }}
    </button>
  </nav>
</template>
