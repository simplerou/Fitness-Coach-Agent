<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: string
  options: Array<{ value: string; label: string }>
  placeholder?: string
  label?: string
  ariaLabel?: string
  disabled?: boolean
}>(), { placeholder: '请选择', disabled: false })
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const root = ref<HTMLElement | null>(null)
const open = ref(false)
const currentLabel = computed(() => props.options.find((item) => item.value === props.modelValue)?.label || props.placeholder)

function choose(value: string) {
  emit('update:modelValue', value)
  open.value = false
}
function closeOutside(event: PointerEvent) {
  if (root.value && !root.value.contains(event.target as Node)) open.value = false
}
function keydown(event: KeyboardEvent) {
  if (event.key === 'Escape') open.value = false
}
onMounted(() => { document.addEventListener('pointerdown', closeOutside); document.addEventListener('keydown', keydown) })
onBeforeUnmount(() => { document.removeEventListener('pointerdown', closeOutside); document.removeEventListener('keydown', keydown) })
</script>

<template>
  <div ref="root" class="filter-select">
    <span v-if="label" class="filter-select-label">{{ label }}</span>
    <button class="filter-select-trigger" type="button" :aria-label="ariaLabel || label" :aria-expanded="open" aria-haspopup="listbox" :disabled="disabled" @click="open = !open">
      <span>{{ currentLabel }}</span><svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 7.5 5 5 5-5" /></svg>
    </button>
    <div v-if="open" class="filter-select-menu" role="listbox" :aria-label="ariaLabel || label || '选项'">
      <button v-for="item in options" :key="item.value" type="button" role="option" :aria-selected="modelValue === item.value" @click="choose(item.value)">
        <span>{{ item.label }}</span><svg v-if="modelValue === item.value" viewBox="0 0 20 20" aria-hidden="true"><path d="m4.5 10 3.2 3.2 7.8-7.8" /></svg>
      </button>
    </div>
  </div>
</template>
