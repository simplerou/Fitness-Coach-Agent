<script setup lang="ts">
import ExerciseLibrary from './ExerciseLibrary.vue'
import ExerciseDetailDialog from './ExerciseDetailDialog.vue'
import { computed, ref } from 'vue'
import { useTrainingStore } from '@/stores/training'
import type { ExerciseDefinition, ExerciseEntryPayload } from '@/api/types'

const props = defineProps<{ modelValue: ExerciseEntryPayload[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: ExerciseEntryPayload[]] }>()
const store = useTrainingStore()
const showLibrary = ref(false)
const active = ref<ExerciseDefinition | null>(null)
const rows = computed(() => props.modelValue.map((row) => ({ row, definition: store.exercises.find((item) => item.id === row.exercise_id) })))
function add(item: ExerciseDefinition): void {
  if (!props.modelValue.some((row) => row.exercise_id === item.id)) emit('update:modelValue', [...props.modelValue, { exercise_id: item.id, sets: 3, reps: 8, target_reps_min: 8, target_reps_max: 12, weight_kg: 0, rpe: 7, completion: 'completed' }])
  showLibrary.value = false
}
function update(index: number, key: keyof ExerciseEntryPayload, value: string | number): void {
  const next = props.modelValue.map((row) => ({ ...row }))
  ;(next[index] as Record<string, unknown>)[key] = typeof value === 'string' ? Number(value) : value
  emit('update:modelValue', next)
}
function remove(index: number): void { emit('update:modelValue', props.modelValue.filter((_, rowIndex) => rowIndex !== index)) }
</script>

<template>
  <fieldset class="exercise-entry-editor"><legend>动作明细</legend>
    <div v-for="(item, index) in rows" :key="item.row.exercise_id" class="exercise-entry-row">
      <div class="exercise-entry-head"><button type="button" class="text-button" @click="active = item.definition || null">{{ item.definition?.name || `动作 #${item.row.exercise_id}` }}</button><button type="button" class="text-button danger" @click="remove(index)">移除</button></div>
      <div class="exercise-entry-fields"><label>组数<input :value="item.row.sets" type="number" min="1" max="20" @input="update(index, 'sets', ($event.target as HTMLInputElement).value)" /></label><label>完成次数<input :value="item.row.reps" type="number" min="1" max="100" @input="update(index, 'reps', ($event.target as HTMLInputElement).value)" /></label><label>目标下限<input :value="item.row.target_reps_min" type="number" min="1" max="100" @input="update(index, 'target_reps_min', ($event.target as HTMLInputElement).value)" /></label><label>目标上限<input :value="item.row.target_reps_max" type="number" min="1" max="100" @input="update(index, 'target_reps_max', ($event.target as HTMLInputElement).value)" /></label><label>重量 kg<input :value="item.row.weight_kg" type="number" min="0" max="1000" step="0.5" @input="update(index, 'weight_kg', ($event.target as HTMLInputElement).value)" /></label><label>动作 RPE<input :value="item.row.rpe" type="number" min="1" max="10" @input="update(index, 'rpe', ($event.target as HTMLInputElement).value)" /></label></div>
    </div>
    <button class="button button-quiet" type="button" @click="showLibrary = !showLibrary">{{ showLibrary ? '收起动作库' : '+ 添加训练动作' }}</button>
    <ExerciseLibrary v-if="showLibrary" compact selectable @select="add" />
    <ExerciseDetailDialog :exercise="active" @close="active = null" />
  </fieldset>
</template>
