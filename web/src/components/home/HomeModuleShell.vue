<script setup lang="ts">
import type { HomeModuleId } from '@/stores/home'

defineProps<{ id: HomeModuleId; title: string; eyebrow: string; collapsed: boolean; first: boolean; last: boolean }>()
const emit = defineEmits<{
  toggle: []; move: [offset: -1 | 1]; dragstart: [id: HomeModuleId]; drop: [id: HomeModuleId]
}>()
</script>

<template>
  <section
    class="home-module"
    :class="[`home-module-${id}`, { 'is-collapsed': collapsed }]"
    draggable="true"
    @dragstart="emit('dragstart', id)"
    @dragover.prevent
    @drop.prevent="emit('drop', id)"
  >
    <header class="home-module-head">
      <div><p class="eyebrow">{{ eyebrow }}</p><h2>{{ title }}</h2></div>
      <div class="home-module-controls" aria-label="模块布局控制">
        <button type="button" :disabled="first" :aria-label="`上移${title}`" @click="emit('move', -1)">↑</button>
        <button type="button" :disabled="last" :aria-label="`下移${title}`" @click="emit('move', 1)">↓</button>
        <button type="button" :aria-expanded="!collapsed" :aria-label="collapsed ? `展开${title}` : `折叠${title}`" @click="emit('toggle')">
          {{ collapsed ? '展开' : '收起' }}
        </button>
      </div>
    </header>
    <div v-show="!collapsed" class="home-module-body"><slot /></div>
  </section>
</template>
