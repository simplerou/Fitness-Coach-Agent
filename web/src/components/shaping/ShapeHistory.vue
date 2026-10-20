<script setup lang="ts">
import { computed, ref } from 'vue'
import { useShapingStore } from '@/stores/shaping'
import { useNotice } from '@/composables/useNotice'
import { SHAPE_METRICS, SHAPE_LABELS, SHAPE_UNITS, SOURCE_LABELS } from '@/constants/shaping'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
defineEmits<{ edit: [date: string] }>()
const shaping = useShapingStore()
const notice = useNotice()
const count = ref(10)
const rows = computed(() => [...shaping.measurements].reverse().slice(0, count.value))
const confirmOpen = ref(false)
const deletingDate = ref('')
function askDelete(date: string): void { deletingDate.value = date; confirmOpen.value = true }
async function remove(): Promise<void> {
  const date = deletingDate.value
  confirmOpen.value = false
  try { notice.notify(await shaping.removeMeasurement(date), 'success') }
  catch (cause) { notice.notify(cause instanceof Error ? cause.message : '测量记录删除失败。', 'error') }
}
</script>

<template>
  <article class="panel shape-panel"><div class="panel-head"><div><p class="eyebrow">YOUR MEASUREMENT LOG</p><h3>测量历史</h3></div><span class="tag">{{ shaping.measurements.length }} 次记录</span></div>
    <p v-if="!rows.length" class="shape-muted">尚未记录测量。留空表示未测量，不代表没有变化。</p>
    <div v-else class="shape-table-scroll" tabindex="0" role="region" aria-label="测量历史，可横向滚动"><table class="shape-history"><thead><tr><th>日期</th><th v-for="metric in SHAPE_METRICS" :key="metric">{{ SHAPE_LABELS[metric] }}<small>{{ SHAPE_UNITS[metric] }}</small></th><th>体成分来源</th><th>操作</th></tr></thead><tbody><tr v-for="row in rows" :key="row.recorded_on"><th scope="row">{{ row.recorded_on }}</th><td v-for="metric in SHAPE_METRICS" :key="metric">{{ row[metric]?.toFixed(1) ?? '未记录' }}</td><td>{{ row.composition_source ? SOURCE_LABELS[row.composition_source] : '—' }}</td><td><div class="shape-table-actions"><button class="text-button" :disabled="shaping.saving" @click="$emit('edit', row.recorded_on)">修改</button><button class="text-button shape-danger-text" :disabled="shaping.saving" @click="askDelete(row.recorded_on)">删除</button></div></td></tr></tbody></table></div>
    <button v-if="count < shaping.measurements.length" class="text-button shape-load-more" @click="count += 10">显示更多记录</button>
    <ConfirmDialog v-model:open="confirmOpen" title="删除这天的测量记录？" :description="`${deletingDate} 的围度和体成分将被删除，照片及体重历史保留；目标起点和已解锁节点保留，当前进度会重新计算。`" confirm-text="删除测量" danger @confirm="remove" />
  </article>
</template>
