<script setup lang="ts">
import { onMounted } from 'vue'
import { useSafetyStore } from '@/stores/safety'
import SafetyCheckCard from '@/components/today/SafetyCheckCard.vue'
import TodayStatusCard from '@/components/today/TodayStatusCard.vue'
import DailySignalForm from '@/components/today/DailySignalForm.vue'
import PlanPeek from '@/components/today/PlanPeek.vue'
import ShapingReminder from '@/components/shaping/ShapingReminder.vue'

const safety = useSafetyStore()
onMounted(() => { void safety.refreshToday() })
</script>

<template>
  <section class="page active">
    <div class="section-heading">
      <div><p class="eyebrow">TODAY</p><h2>今天怎么练</h2></div>
      <button class="button button-quiet" type="button" :disabled="safety.loading" @click="safety.refreshToday">刷新状态</button>
    </div>
    <SafetyCheckCard />
    <TodayStatusCard />
    <ShapingReminder />
    <div class="grid two-col">
      <DailySignalForm />
      <PlanPeek />
    </div>
  </section>
</template>
