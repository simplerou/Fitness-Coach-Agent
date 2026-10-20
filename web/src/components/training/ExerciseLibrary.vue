<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useTrainingStore } from '@/stores/training'
import ExerciseDetailDialog from './ExerciseDetailDialog.vue'
import type { ExerciseDefinition } from '@/api/types'

const props = withDefaults(defineProps<{ compact?: boolean; selectable?: boolean }>(), { compact: false, selectable: false })
const emit = defineEmits<{ select: [exercise: ExerciseDefinition] }>()
const store = useTrainingStore()
const query = ref('')
const category = ref('')
const active = ref<ExerciseDefinition | null>(null)
const filtered = computed(() => store.exercises.filter((item) => (!category.value || item.category === category.value)
  && (!query.value.trim() || `${item.name}${item.target_muscles.join('')}`.includes(query.value.trim()))))
onMounted(() => { if (!store.exercises.length) void store.loadExercises() })
</script>

<template>
  <div class="exercise-library" :class="{ compact }">
    <div class="exercise-library-tools"><input v-model="query" type="search" placeholder="搜索动作或目标肌群" aria-label="搜索动作" /><select v-model="category" aria-label="筛选部位"><option value="">全部部位</option><option v-for="item in ['胸','背','腿','肩','臂','核心']" :key="item">{{ item }}</option></select></div>
    <div class="exercise-library-list">
      <article v-for="item in filtered" :key="item.id" class="exercise-library-item">
        <button type="button" @click="active = item"><b>{{ item.name }}</b><span>{{ item.category }} · {{ item.target_muscles.join('、') }}</span></button>
        <button v-if="selectable" class="text-button" type="button" @click="emit('select', item)">添加</button>
      </article>
      <p v-if="!filtered.length" class="fine-print">没有找到匹配动作。</p>
    </div>
    <ExerciseDetailDialog :exercise="active" @close="active = null" />
  </div>
</template>
