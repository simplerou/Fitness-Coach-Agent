<script setup lang="ts">
import { computed, ref } from 'vue'
import { useTrainingStore } from '@/stores/training'
import { useShapingIntelligenceStore } from '@/stores/shapingIntelligence'
import { useNotice } from '@/composables/useNotice'
import AdviceCard from '@/components/ui/AdviceCard.vue'
import { useCoachWindow } from '@/composables/useCoachWindow'

type Card = { kind: 'progression' | 'weak'; id: number; title: string; body: string; detail: string }
const training = useTrainingStore()
const intelligence = useShapingIntelligenceStore()
const coach = useCoachWindow()
const notice = useNotice()
const recent = ref<{ card: Card; decision: 'adopted' | 'ignored' } | null>(null)
const cards = computed<Card[]>(() => [
  ...training.logs.flatMap(log => log.advice).filter(item => item.status === 'pending').map(item => ({
    kind: 'progression' as const, id: item.id, title: `${item.exercise_name} · ${typeLabel(item.advice_type)}`,
    body: item.reason, detail: `${item.prescription.sets} 组 × ${item.prescription.reps} 次 · ${item.prescription.weight_kg} kg`,
  })),
  ...(intelligence.weakAnalysis?.advice.filter(item => item.status === 'pending').map(item => ({
    kind: 'weak' as const, id: item.id, title: `${item.muscle_group}专项加练`, body: item.evidence,
    detail: `${item.prescription} · ${item.integration}`,
  })) ?? []),
].slice(0, 2))
function typeLabel(type: 'weight' | 'reps' | 'sets'): string { return ({ weight: '建议加重', reps: '建议加次数', sets: '建议加组' })[type] }
async function decide(card: Card, decision: 'adopted' | 'ignored'): Promise<void> {
  try {
    const message = card.kind === 'progression' ? await training.resolveAdvice(card.id, decision) : await intelligence.decideWeak(card.id, decision)
    recent.value = { card, decision }
    notice.notify(message, decision === 'adopted' ? 'success' : 'info')
  } catch (error) { notice.notify(error instanceof Error ? error.message : '请求失败，请稍后重试。', 'error') }
}
async function undo(): Promise<void> {
  if (!recent.value) return
  try {
    const { card } = recent.value
    const message = card.kind === 'progression' ? await training.undoAdvice(card.id) : await intelligence.undoWeak(card.id)
    recent.value = null
    notice.notify(message, 'info')
  } catch (error) { notice.notify(error instanceof Error ? error.message : '请求失败，请稍后重试。', 'error') }
}
</script>
<template>
  <div v-if="cards.length" class="home-smart-list"><AdviceCard v-for="card in cards" :key="`${card.kind}-${card.id}`" :title="card.title" :evidence="card.body" :impact="card.detail" @adopt="decide(card, 'adopted')" @ignore="decide(card, 'ignored')" /></div>
  <div v-else class="home-smart-empty"><div><strong>今天没有需要优先处理的建议</strong><p>系统只展示有记录依据的建议，不会为了填满首页而生成结论。</p></div><button class="button button-quiet" @click="coach.openCoach()">问问教练</button></div>
  <div v-if="recent" class="home-advice-undo" role="status"><span>“{{ recent.card.title }}”已{{ recent.decision === 'adopted' ? '采纳' : '忽略' }}。</span><button class="text-button" @click="undo">撤销本次操作</button></div>
</template>
