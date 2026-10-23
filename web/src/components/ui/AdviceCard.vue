<script setup lang="ts">
defineProps<{
  title: string
  evidence: string
  impact: string
  status?: 'pending' | 'adopted' | 'ignored'
  loading?: boolean
  undoable?: boolean
}>()
defineEmits<{ adopt: []; ignore: []; undo: [] }>()
</script>

<template>
  <article class="advice-card">
    <div class="advice-label">
      <span>AI 建议</span>
      <b v-if="status && status !== 'pending'">{{ status === 'adopted' ? '已采纳' : '已忽略' }}</b>
    </div>
    <h3>{{ title }}</h3>
    <dl>
      <div><dt>依据</dt><dd>{{ evidence }}</dd></div>
      <div><dt>预期影响</dt><dd>{{ impact }}</dd></div>
    </dl>
    <slot />
    <div class="advice-card-actions">
      <template v-if="!status || status === 'pending'">
        <button class="button button-primary" :disabled="loading" @click="$emit('adopt')">采纳</button>
        <button class="button button-quiet" :disabled="loading" @click="$emit('ignore')">忽略</button>
      </template>
      <button v-else-if="undoable !== false" class="text-button" :disabled="loading" @click="$emit('undo')">撤销处理</button>
    </div>
  </article>
</template>
