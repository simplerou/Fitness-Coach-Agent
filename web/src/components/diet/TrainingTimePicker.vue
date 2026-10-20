<script setup lang="ts">
import { computed, ref } from 'vue'
import BaseDialog from '@/components/common/BaseDialog.vue'
import { useNotice } from '@/composables/useNotice'

const props = defineProps<{ start: string | null; end: string | null }>()
const emit = defineEmits<{ update: [start: string | null, end: string | null] }>()
const notice = useNotice()
const dialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const start = ref('18:00')
const end = ref('19:00')
const hours = Array.from({ length: 24 }, (_, index) => String(index).padStart(2, '0'))
const minutes = Array.from({ length: 60 }, (_, index) => String(index).padStart(2, '0'))
const parts = (value: string) => value.split(':')
const startHour = computed({ get: () => parts(start.value)[0], set: (value) => { start.value = `${value}:${parts(start.value)[1]}` } })
const startMinute = computed({ get: () => parts(start.value)[1], set: (value) => { start.value = `${parts(start.value)[0]}:${value}` } })
const endHour = computed({ get: () => parts(end.value)[0], set: (value) => { end.value = `${value}:${parts(end.value)[1]}` } })
const endMinute = computed({ get: () => parts(end.value)[1], set: (value) => { end.value = `${parts(end.value)[0]}:${value}` } })
function open(): void {
  const currentStart = props.start || '18:00'
  const minutesFromMidnight = Number(currentStart.slice(0, 2)) * 60 + Number(currentStart.slice(3))
  const defaultEndMinutes = Math.min(minutesFromMidnight + 60, 23 * 60 + 59)
  start.value = currentStart
  end.value = props.end || `${String(Math.floor(defaultEndMinutes / 60)).padStart(2, '0')}:${String(defaultEndMinutes % 60).padStart(2, '0')}`
  dialog.value?.open()
}
function apply(): void {
  const toMinutes = (value: string) => Number(value.slice(0, 2)) * 60 + Number(value.slice(3))
  if (toMinutes(end.value) <= toMinutes(start.value)) { notice.notify('训练结束时间需要晚于开始时间。', 'error'); return }
  emit('update', start.value, end.value)
  dialog.value?.close()
}
function clear(): void { emit('update', null, null); dialog.value?.close() }
defineExpose({ open })
</script>

<template>
  <BaseDialog ref="dialog" class="user-dialog training-time-dialog" aria-labelledby="training-time-title">
    <div class="user-dialog-top"><div><p class="eyebrow">TRAINING TIME</p><h2 id="training-time-title">选择训练时间</h2></div><button class="user-dialog-close" type="button" aria-label="关闭时间选择" @click="dialog?.close()">×</button></div>
    <p class="training-time-picker-help">分别设置开始与结束时间，均使用 24 小时制。</p>
    <div class="training-time-range-selectors"><fieldset><legend>开始时间</legend><div><select v-model="startHour" aria-label="开始小时"><option v-for="hour in hours" :key="hour">{{ hour }}</option></select><span>:</span><select v-model="startMinute" aria-label="开始分钟"><option v-for="minute in minutes" :key="minute">{{ minute }}</option></select></div></fieldset><fieldset><legend>结束时间</legend><div><select v-model="endHour" aria-label="结束小时"><option v-for="hour in hours" :key="hour">{{ hour }}</option></select><span>:</span><select v-model="endMinute" aria-label="结束分钟"><option v-for="minute in minutes" :key="minute">{{ minute }}</option></select></div></fieldset></div>
    <div class="account-dialog-actions training-time-actions"><button class="button button-quiet" type="button" @click="clear">清除</button><button class="button button-quiet" type="button" @click="dialog?.close()">取消</button><button class="button button-primary" type="button" @click="apply">确定</button></div>
  </BaseDialog>
</template>
