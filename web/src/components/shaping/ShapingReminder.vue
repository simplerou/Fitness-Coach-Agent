<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useShapingStore } from '@/stores/shaping'
import { SHAPE_LABELS } from '@/constants/shaping'
const router = useRouter()
const shaping = useShapingStore()
const due = computed(() => shaping.reminders.filter(row => row.due))
const labels = computed(() => due.value.map(row => SHAPE_LABELS[row.metric]).join('、'))
onMounted(async () => { try { await shaping.load() } catch { /* Optional reminder; shaping page provides retry. */ } })
</script>

<template>
  <aside v-if="due.length" class="shape-reminder shape-today-reminder is-due" role="status"><div><b>围度双周复测提醒</b><p>{{ labels }}距离上次测量已满两周。用相同条件留下一次记录，慢慢看见变化。</p></div><button class="button button-quiet" @click="router.push({ name: 'shaping' })">去塑型追踪</button></aside>
</template>
