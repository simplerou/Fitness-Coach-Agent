<script setup lang="ts">
import { computed, ref } from 'vue'

export interface TableColumn { key: string; label: string; editable?: boolean; width?: string }
const props = defineProps<{
  columns: TableColumn[]
  rows: Array<Record<string, unknown>>
  rowKey: string
  emptyText?: string
}>()
const emit = defineEmits<{
  edit: [row: Record<string, unknown>, key: string, value: string]
  select: [rows: Record<string, unknown>[]]
}>()
const editing = ref('')
const draft = ref('')
const selected = ref(new Set<unknown>())
const sortKey = ref('')
const sortDirection = ref<'asc' | 'desc'>('asc')
const sortedRows = computed(() => {
  if (!sortKey.value) return props.rows
  return [...props.rows].sort((left, right) => {
    const a = String(left[sortKey.value] ?? '')
    const b = String(right[sortKey.value] ?? '')
    return a.localeCompare(b, 'zh-CN', { numeric: true }) * (sortDirection.value === 'asc' ? 1 : -1)
  })
})

function start(row: Record<string, unknown>, column: TableColumn) {
  if (!column.editable) return
  editing.value = `${row[props.rowKey]}:${column.key}`
  draft.value = String(row[column.key] ?? '')
}
function save(row: Record<string, unknown>, key: string) {
  emit('edit', row, key, draft.value)
  editing.value = ''
}
function toggle(row: Record<string, unknown>) {
  const next = new Set(selected.value)
  const id = row[props.rowKey]
  next.has(id) ? next.delete(id) : next.add(id)
  selected.value = next
  emit('select', props.rows.filter((item) => next.has(item[props.rowKey])))
}
function sort(key: string) {
  if (sortKey.value === key) sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  else { sortKey.value = key; sortDirection.value = 'asc' }
}
function toggleAll() {
  selected.value = selected.value.size === props.rows.length ? new Set() : new Set(props.rows.map((row) => row[props.rowKey]))
  emit('select', props.rows.filter((row) => selected.value.has(row[props.rowKey])))
}
</script>

<template>
  <div class="data-table-wrap">
    <table class="data-table">
      <thead><tr><th class="select-cell"><input type="checkbox" :checked="Boolean(rows.length) && selected.size === rows.length" aria-label="选择全部" @change="toggleAll" /></th><th v-for="column in columns" :key="column.key" :style="{ width: column.width }"><button class="table-sort" @click="sort(column.key)">{{ column.label }}<span v-if="sortKey === column.key" aria-hidden="true">{{ sortDirection === 'asc' ? '↑' : '↓' }}</span></button></th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="row in sortedRows" :key="String(row[rowKey])">
          <td class="select-cell"><input type="checkbox" :checked="selected.has(row[rowKey])" @change="toggle(row)" /></td>
          <td v-for="column in columns" :key="column.key" @dblclick="start(row, column)">
            <input v-if="editing === `${row[rowKey]}:${column.key}`" v-model="draft" @keydown.enter.prevent="save(row, column.key)" @keydown.esc.prevent="editing = ''" @blur="save(row, column.key)" />
            <slot v-else :name="`cell-${column.key}`" :row="row" :value="row[column.key]">{{ row[column.key] ?? '未记录' }}</slot>
          </td>
          <td><slot name="actions" :row="row" /></td>
        </tr>
      </tbody>
    </table>
    <div v-if="!rows.length" class="table-empty"><span>{{ emptyText || '暂无记录' }}</span><slot name="empty-action" /></div>
  </div>
</template>
