<script setup lang="ts">
import type { CoachAnswerResponse } from '@/api/types'
import { exerciseNameLabel } from '@/utils/exerciseLabels'
import CoachActionCard from './CoachActionCard.vue'
defineProps<{ response: CoachAnswerResponse }>()
</script>

<template>
  <article class="coach-agent-message">
    <div class="coach-answer-kind"><span>{{ response.agent_mode === 'react' ? 'ReAct Agent' : '本地答复' }}</span><small>{{ response.model_note }}</small></div>
    <p>{{ response.answer }}</p>
    <p v-if="response.safety_note" class="coach-safety-note">{{ response.safety_note }}</p>
    <p v-if="response.stop_reason === 'tool_limit' || response.stop_reason === 'time_limit'" class="coach-safety-note">本轮已达到查询次数或耗时上限，回答仅基于已获取的数据。</p>
    <details v-if="response.tool_trace?.length" class="coach-sources">
      <summary>本次使用了 {{ response.tool_trace.length }} 次工具</summary>
      <article v-for="(step, index) in response.tool_trace" :key="index">
        <b>{{ index + 1 }}. {{ step.label }} · {{ step.status === 'success' ? '完成' : '未完成' }}</b>
        <p>{{ step.summary }}</p>
      </article>
    </details>
    <CoachActionCard v-for="action in response.actions" :key="action.id" :action="action" @resolved="Object.assign(action, $event)" />
    <div v-if="response.references.length" class="coach-related-actions"><b>相关动作</b><div><span v-for="item in response.references" :key="item.id">{{ exerciseNameLabel(item.name) }}</span></div></div>
    <details v-if="response.knowledge_sources.length" class="coach-sources">
      <summary>查看 {{ response.knowledge_sources.length }} 条检索资料</summary>
      <article v-for="source in response.knowledge_sources" :key="source.document_key">
        <b>{{ source.title }}</b><small>{{ source.source_name }}<template v-if="source.source_published_at"> · {{ source.source_published_at }}</template></small>
        <p>{{ source.excerpt }}</p><a v-if="source.source_url" :href="source.source_url" target="_blank" rel="noopener noreferrer">查看来源</a>
      </article>
    </details>
  </article>
</template>
