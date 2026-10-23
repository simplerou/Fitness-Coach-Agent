<script setup lang="ts">
import { ref, watch } from 'vue'
import AdviceCard from '@/components/ui/AdviceCard.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import { decideCoachAction } from '@/api/coach'
import type { CoachAction } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { useDietStore } from '@/stores/diet'
import { usePlanStore } from '@/stores/plan'
import { useShapingIntelligenceStore } from '@/stores/shapingIntelligence'

const props = defineProps<{ action: CoachAction }>()
const emit = defineEmits<{ resolved: [action: CoachAction] }>()
const auth = useAuthStore()
const diet = useDietStore()
const plan = usePlanStore()
const intelligence = useShapingIntelligenceStore()
const open = ref(false)
const busy = ref(false)
const message = ref('')
const error = ref('')
const status = ref(props.action.status)
watch(() => props.action.status, value => { status.value = value })

async function decide(decision: 'adopted' | 'ignored'): Promise<void> {
  if (busy.value || status.value !== 'pending') return
  busy.value = true; error.value = ''; open.value = false
  const userId = auth.user?.id
  try {
    const result = await decideCoachAction(props.action.id, decision)
    if (auth.user?.id !== userId) return
    status.value = result.action.status
    message.value = result.message
    emit('resolved', result.action)
    if (decision === 'adopted') {
      const refreshes = props.action.kind === 'diet_target'
        ? [diet.loadTargets(), diet.loadLog(), intelligence.loadDietAdjustment(props.action.target_date)]
        : [plan.loadCurrent(), plan.loadHistory()]
      const refreshed = await Promise.allSettled(refreshes)
      if (refreshed.some(item => item.status === 'rejected')) {
        message.value += ' 部分页面数据刷新失败，可在对应页面重试刷新。'
      }
    }
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '草案暂时无法处理，请重试。' }
  finally { busy.value = false }
}
</script>

<template>
  <AdviceCard class="coach-action-card" :title="action.title" :evidence="action.summary" :impact="action.impact"
    :status="status" :loading="busy" :undoable="false" @adopt="open = true" @ignore="decide('ignored')">
    <ul><li v-for="detail in action.details" :key="detail">{{ detail }}</li></ul>
    <p v-if="status !== 'pending'" role="status">{{ message || (status === 'adopted' ? '已确认保存' : '已取消，原设置未改变') }}</p>
    <p v-if="error" class="coach-inline-error" role="alert">{{ error }}</p>
  </AdviceCard>
  <ConfirmDialog v-model:open="open" :title="action.title" :description="action.impact + ' 请确认以上具体数值和变更范围；确认后将保存。'"
    :danger="action.kind === 'plan_adjustment'" confirm-text="确认保存" @confirm="decide('adopted')" />
</template>
