<script setup lang="ts">
import { useDietStore } from '@/stores/diet'
import DietPlanner from '@/components/diet/DietPlanner.vue'

const diet = useDietStore()
const props = defineProps<{ consent: boolean }>()
const emit = defineEmits<{ generate: []; 'open-weekly': []; 'update:consent': [value: boolean] }>()

function selectPlan(index: number): void {
  diet.plan = diet.planHistory[index]?.plan_data ?? null
  emit('open-weekly')
}

function dateLabel(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN')
}
</script>

<template>
  <section class="panel diet-planning-records">
    <header class="panel-head">
      <div><p class="eyebrow">SAVED PLANS</p><h2>饮食规划记录</h2><p>每次 AI 生成后都会保存一份快照，点击记录可查看对应的一周计划。</p></div>
      <div class="diet-record-actions">
        <button class="button button-quiet" type="button" :disabled="diet.generatingPlan" @click="diet.loadHistory">刷新记录</button>
        <button class="button button-primary" type="button" :disabled="diet.generatingPlan" @click="emit('generate')">{{ diet.generatingPlan ? 'AI 正在生成…' : 'AI 生成' }}</button>
      </div>
    </header>
    <DietPlanner :consent="props.consent" @update:consent="emit('update:consent', $event)" />
    <div v-if="diet.planHistory.length" class="diet-history-list">
      <button v-for="(item,index) in diet.planHistory" :key="item.id" class="diet-history-item" type="button" @click="selectPlan(index)">
        <span><strong>{{ dateLabel(item.created_at) }}</strong><small>计划日期：{{ item.generated_on }}</small></span>
        <span>{{ item.plan_data.summary?.goal || '饮食规划' }} · {{ item.plan_data.target?.calories_kcal ?? '未记录' }} kcal/日</span>
        <span class="text-button">查看一周计划 →</span>
      </button>
    </div>
    <div v-else class="empty-state">
      <p>还没有饮食规划记录。填写饮食档案和 AI 数据授权后，可生成并保存第一份计划。</p>
      <button class="button button-primary" type="button" :disabled="diet.generatingPlan" @click="emit('generate')">AI 生成第一份计划</button>
    </div>
  </section>
</template>
