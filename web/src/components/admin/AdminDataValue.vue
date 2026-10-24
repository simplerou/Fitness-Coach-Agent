<script setup lang="ts">
import { computed } from 'vue'
import { businessEntries, fieldLabel, formatValue, isObject, itemHeading, listField, normalizeValue, safeLink } from '@/utils/adminPresentation'

const props = withDefaults(defineProps<{
  value: unknown
  field: string
  dataset?: string
  exerciseNames?: Record<string, string>
  metric?: string
  omitFields?: string[]
}>(), { dataset: '', exerciseNames: () => ({}), omitFields: () => [] })

const data = computed(() => normalizeValue(props.value, props.field))
const object = computed(() => isObject(data.value) ? data.value : null)
const entries = computed(() => object.value ? businessEntries(object.value, props.omitFields) : [])
const array = computed<unknown[]>(() => Array.isArray(data.value) ? data.value : [])
const metric = computed(() => typeof object.value?.metric === 'string' ? object.value.metric : props.metric)
const context = computed(() => ({ dataset: props.dataset, exerciseNames: props.exerciseNames, metric: metric.value }))
const primitiveList = computed(() => array.value.every(value => !isObject(value) && !Array.isArray(value)))
const tableRows = computed<Record<string, unknown>[]>(() => {
  if (!array.value.length || !array.value.every(value => isObject(value) && businessEntries(value).length &&
    businessEntries(value).every(([, cell]) => !isObject(cell) && (!Array.isArray(cell) || cell.every(item => !isObject(item) && !Array.isArray(item)))))) return []
  return array.value as Record<string, unknown>[]
})
const columns = computed(() => [...new Set(tableRows.value.flatMap(row => businessEntries(row).map(([key]) => key)))])
const link = computed(() => ['url', 'source_url', 'link', 'demo_video_url', 'demo_images', 'media_source_url'].includes(props.field) ? safeLink(data.value) : null)
function wide(value: unknown, field: string): boolean {
  return isObject(value) || Array.isArray(value) || (typeof value === 'string' && (value.length > 90 || ['question', 'answer', 'note', 'description', 'reason', 'message', 'summary', 'calculation', 'impact', 'notice'].includes(field)))
}
function headingFields(value: unknown): string[] {
  return isObject(value) ? ['title', 'name', 'exercise_name', 'planned_session_title'].filter(key => typeof value[key] === 'string') : []
}
</script>

<template>
  <span v-if="data === null || data === undefined || data === ''" class="admin-value-empty">未记录</span>
  <template v-else-if="Array.isArray(data)">
    <span v-if="!array.length" class="admin-value-empty">暂无条目</span>
    <ul v-else-if="primitiveList" class="admin-value-list" :class="{ 'is-compact': ['equipment', 'weekdays', 'training_weekdays', 'rest_weekdays', 'training_days', 'exercise_ids', 'preferred_exercise_ids', 'referenced_exercise_ids', 'target_muscles', 'focus_groups', 'excluded_groups', 'milestones'].includes(field) }">
      <li v-for="(item, index) in array" :key="index">{{ formatValue(listField(field), item, context) }}</li>
    </ul>
    <div v-else-if="tableRows.length" class="admin-value-table-wrap" tabindex="0" :aria-label="fieldLabel(field, dataset) + '表格，可横向滚动'">
      <table class="admin-value-table">
        <caption>{{ fieldLabel(field, dataset) }}</caption>
        <thead><tr><th v-for="column in columns" :key="column" scope="col">{{ fieldLabel(column, dataset) }}</th></tr></thead>
        <tbody><tr v-for="(row, index) in tableRows" :key="index"><td v-for="column in columns" :key="column">
          <AdminDataValue :value="row[column]" :field="column" :dataset="dataset" :exercise-names="exerciseNames" :metric="typeof row.metric === 'string' ? row.metric : metric" />
        </td></tr></tbody>
      </table>
    </div>
    <div v-else class="admin-value-cards">
      <section v-for="(item, index) in array" :key="index" class="admin-value-card">
        <h5>{{ itemHeading(item, index, field, dataset) }}</h5>
        <AdminDataValue :value="item" :field="field" :dataset="dataset" :exercise-names="exerciseNames" :metric="metric" :omit-fields="headingFields(item)" />
      </section>
    </div>
  </template>
  <template v-else-if="object">
    <span v-if="!entries.length" class="admin-value-empty">暂无内容</span>
    <dl v-else class="admin-business-grid">
      <div v-for="([key, value]) in entries" :key="key" class="admin-business-field" :class="{ 'is-wide': wide(normalizeValue(value, key), key) }">
        <dt>{{ fieldLabel(key, dataset) }}</dt>
        <dd><AdminDataValue :value="value" :field="key" :dataset="dataset" :exercise-names="exerciseNames" :metric="metric" /></dd>
      </div>
    </dl>
  </template>
  <a v-else-if="link" :href="link" target="_blank" rel="noopener noreferrer" class="admin-business-link">打开资料链接 ↗</a>
  <span v-else class="admin-business-text">{{ formatValue(field, data, context) }}</span>
</template>
