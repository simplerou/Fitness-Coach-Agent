<script setup lang="ts">
import { computed, ref } from 'vue'
import { useNotice } from '@/composables/useNotice'
import FilterSelect from '@/components/ui/FilterSelect.vue'

const props = defineProps<{ start: string | null; end: string | null }>()
const emit = defineEmits<{ update: [start: string | null, end: string | null] }>()
const notice = useNotice()
const isOpen = ref(false)
const start = ref('18:00')
const end = ref('19:00')
const hours = Array.from({ length: 24 }, (_, index) => String(index).padStart(2, '0'))
const minutes = Array.from({ length: 60 }, (_, index) => String(index).padStart(2, '0'))
const hourOptions = hours.map(value => ({ value, label: value }))
const minuteOptions = minutes.map(value => ({ value, label: value }))
const parts = (value: string) => value.split(':')
const startHour = computed({ get: () => parts(start.value)[0], set: (value) => { start.value = `${value}:${parts(start.value)[1]}` } })
const startMinute = computed({ get: () => parts(start.value)[1], set: (value) => { start.value = `${parts(start.value)[0]}:${value}` } })
const endHour = computed({ get: () => parts(end.value)[0], set: (value) => { end.value = `${value}:${parts(end.value)[1]}` } })
const endMinute = computed({ get: () => parts(end.value)[1], set: (value) => { end.value = `${parts(end.value)[0]}:${value}` } })
const label = computed(() => props.start && props.end
  ? `${props.start}–${props.end}`
  : props.start ? `开始 ${props.start}（未设置结束时间）` : '选择开始和结束时间')

function open(): void {
  const currentStart = props.start || '18:00'
  const minutesFromMidnight = Number(currentStart.slice(0, 2)) * 60 + Number(currentStart.slice(3))
  const defaultEndMinutes = Math.min(minutesFromMidnight + 60, 23 * 60 + 59)
  start.value = currentStart
  end.value = props.end || `${String(Math.floor(defaultEndMinutes / 60)).padStart(2, '0')}:${String(defaultEndMinutes % 60).padStart(2, '0')}`
  isOpen.value = true
}

function apply(): void {
  const toMinutes = (value: string) => Number(value.slice(0, 2)) * 60 + Number(value.slice(3))
  if (toMinutes(end.value) <= toMinutes(start.value)) {
    notice.notify('训练结束时间需要晚于开始时间。', 'error')
    return
  }
  emit('update', start.value, end.value)
  isOpen.value = false
}

function clear(): void {
  emit('update', null, null)
  isOpen.value = false
}
</script>

<template>
  <div class="training-time-control">
    <button class="training-time-trigger" type="button" :aria-expanded="isOpen" @click="isOpen ? isOpen = false : open()">{{ label }}</button>
    <div v-if="isOpen" class="training-time-popover">
      <p class="training-time-picker-help">分别设置开始与结束时间，均使用 24 小时制。</p>
      <div class="training-time-range-selectors">
        <fieldset><legend>开始时间</legend><div><FilterSelect v-model="startHour" :options="hourOptions" aria-label="开始小时"/><span>:</span><FilterSelect v-model="startMinute" :options="minuteOptions" aria-label="开始分钟"/></div></fieldset>
        <fieldset><legend>结束时间</legend><div><FilterSelect v-model="endHour" :options="hourOptions" aria-label="结束小时"/><span>:</span><FilterSelect v-model="endMinute" :options="minuteOptions" aria-label="结束分钟"/></div></fieldset>
      </div>
      <div class="training-time-popover-actions"><button class="button button-quiet" type="button" @click="clear">清除</button><button class="button button-quiet" type="button" @click="isOpen = false">取消</button><button class="button button-primary" type="button" @click="apply">确定</button></div>
    </div>
  </div>
</template>

<style scoped>
.training-time-popover{display:grid;gap:14px;margin-top:8px;padding:14px;border:1px solid var(--border);border-radius:var(--r-md);background:var(--surface);box-shadow:var(--shadow-2)}
.training-time-range-selectors{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.training-time-range-selectors fieldset{min-width:0;padding:8px;border-color:var(--border);border-radius:var(--r-sm);background:var(--surface-2)}
.training-time-range-selectors fieldset>div{grid-template-columns:68px auto 68px;justify-content:start;gap:6px}
.training-time-range-selectors select{width:68px;min-width:0;min-height:36px;padding:6px 22px 6px 8px;border-color:var(--border-strong);border-radius:var(--r-sm);background-color:var(--surface);background-position:right 5px center;background-size:14px;color:var(--text-1);font-size:var(--fs-sm)}
.training-time-range-selectors :deep(.filter-select){width:68px;min-width:0}
.training-time-range-selectors :deep(.filter-select-trigger){min-height:36px;padding:0 6px;border-color:var(--border-strong);font-size:var(--fs-sm)}
.training-time-range-selectors :deep(.filter-select-trigger svg){width:14px}
.training-time-range-selectors :deep(.filter-select-menu){right:auto;left:0;min-width:100%;width:max-content;max-width:180px}
.training-time-range-selectors fieldset>div>span{font-size:var(--fs-sm)}
.training-time-popover-actions{display:flex;justify-content:flex-end;gap:8px}
@media(max-width:560px){.training-time-range-selectors{grid-template-columns:1fr}.training-time-popover-actions{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))}.training-time-popover-actions .button{padding-inline:8px}}
</style>
