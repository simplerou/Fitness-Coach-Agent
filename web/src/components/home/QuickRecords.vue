<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
const items = [
  { label: '训练', detail: '记录完成度与 RPE', route: 'log', mark: '01' },
  { label: '饮食', detail: '添加餐食或饮水', route: 'diet', mark: '02' },
  { label: '围度', detail: '记录腰臀胸臂腿', route: 'shaping', query: { section: 'measurements', action: 'record' }, mark: '03' },
  { label: '照片', detail: '正面、侧面、背面', route: 'shaping', query: { section: 'photos' }, mark: '04' },
]
</script>
<template><div class="home-quick-grid"><button v-for="item in items" :key="item.label" @click="router.push({ name: item.route, query: item.query })"><span>{{ item.mark }}</span><div><strong>记录{{ item.label }}</strong><small>{{ item.detail }}</small></div><b aria-hidden="true">→</b></button></div></template>
