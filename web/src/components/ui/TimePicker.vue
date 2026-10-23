<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import FilterSelect from './FilterSelect.vue'

const props = withDefaults(defineProps<{
  modelValue: string | null
  ariaLabel?: string
  defaultTime?: string
}>(), { ariaLabel: '选择时间', defaultTime: '12:00' })
const emit = defineEmits<{ 'update:modelValue': [value: string | null] }>()
const root = ref<HTMLElement | null>(null)
const trigger = ref<HTMLButtonElement | null>(null)
const isOpen = ref(false)
const hour = ref('12')
const minute = ref('00')
const hourOptions = Array.from({ length: 24 }, (_, index) => {
  const value = String(index).padStart(2, '0')
  return { value, label: value }
})
const minuteOptions = Array.from({ length: 60 }, (_, index) => {
  const value = String(index).padStart(2, '0')
  return { value, label: value }
})
function toggle(): void {
  if (isOpen.value) { isOpen.value = false; return }
  const value = props.modelValue || props.defaultTime
  const valid = /^([01]\d|2[0-3]):[0-5]\d$/.test(value) ? value : '12:00'
  hour.value = valid.slice(0, 2)
  minute.value = valid.slice(3, 5)
  isOpen.value = true
}
function close(): void {
  isOpen.value = false
  void nextTick(() => trigger.value?.focus())
}
function apply(): void {
  emit('update:modelValue', hour.value + ':' + minute.value)
  close()
}
function clear(): void {
  emit('update:modelValue', null)
  close()
}
function closeOutside(event: PointerEvent): void {
  if (root.value && !root.value.contains(event.target as Node)) isOpen.value = false
}
function escape(event: KeyboardEvent): void {
  if (!isOpen.value) return
  event.preventDefault()
  event.stopPropagation()
  close()
}
onMounted(() => document.addEventListener('pointerdown', closeOutside))
onBeforeUnmount(() => document.removeEventListener('pointerdown', closeOutside))
</script>

<template>
  <div ref="root" class="time-picker" @keydown.esc="escape">
    <button ref="trigger" class="filter-select-trigger" type="button" :aria-label="ariaLabel" :aria-expanded="isOpen" @click="toggle">
      <span>{{ modelValue || '选择进食时间' }}</span>
      <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 7.5 5 5 5-5"/></svg>
    </button>
    <div v-if="isOpen" class="time-picker-panel" role="group" :aria-label="ariaLabel + '（24小时制）'">
      <p>24 小时制，分别选择小时与分钟。</p>
      <div class="time-picker-selectors">
        <FilterSelect v-model="hour" :options="hourOptions" :aria-label="ariaLabel + '：小时'" />
        <span aria-hidden="true">:</span>
        <FilterSelect v-model="minute" :options="minuteOptions" :aria-label="ariaLabel + '：分钟'" />
      </div>
      <div class="time-picker-actions">
        <button class="button button-quiet" type="button" @click="clear">清除</button>
        <button class="button button-quiet" type="button" @click="close">取消</button>
        <button class="button button-primary" type="button" @click="apply">确定</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.time-picker{width:min(100%,320px)}
.time-picker-panel{display:grid;gap:14px;margin-top:8px;padding:14px;border:1px solid var(--border);border-radius:var(--r-md);background:var(--surface);box-shadow:var(--shadow-2)}
.time-picker-panel>p{margin:0;color:var(--text-2);font-size:var(--fs-sm)}
.time-picker-selectors{display:grid;grid-template-columns:68px auto 68px;justify-content:start;align-items:center;gap:6px;padding:10px;border-radius:var(--r-sm);background:var(--surface-2)}
.time-picker-selectors>span{color:var(--text-2);font-weight:600}
.time-picker-selectors :deep(.filter-select){width:68px;min-width:0}
.time-picker-selectors :deep(.filter-select-trigger){min-height:36px;padding:0 6px;font-size:var(--fs-sm)}
.time-picker-selectors :deep(.filter-select-trigger svg){width:14px}
.time-picker-selectors :deep(.filter-select-menu){right:auto;left:0;width:max-content;min-width:100%;max-width:180px}
.time-picker-actions{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap}
.time-picker-actions .button{min-height:40px;padding-inline:12px}
</style>
