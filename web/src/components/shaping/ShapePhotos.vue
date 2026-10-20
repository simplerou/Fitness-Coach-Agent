<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useShapingStore } from '@/stores/shaping'
import { useNotice } from '@/composables/useNotice'
import { PHOTO_VIEWS, PHOTO_LABELS } from '@/constants/shaping'
import { photoUrl } from '@/utils/shaping'
import { localDateString } from '@/utils/date'
import type { ShapePhoto, ShapePhotoView } from '@/api/types'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import PhotoUploadDialog from './PhotoUploadDialog.vue'
import PhotoCompare from './PhotoCompare.vue'
import ShapeSnapshot from './ShapeSnapshot.vue'
const shaping = useShapingStore()
const notice = useNotice()
const upload = ref<InstanceType<typeof PhotoUploadDialog> | null>(null)
const mode = ref<'period' | 'compare'>('period')
const selected = ref('')
const deleting = ref<ShapePhoto | null>(null)
const confirmOpen = ref(false)
const dates = computed(() => [...new Set(shaping.photos.map(photo => photo.recorded_on))].sort())
const index = computed({ get: () => Math.max(0, dates.value.indexOf(selected.value)), set: value => { selected.value = dates.value[Number(value)] ?? '' } })
watch(dates, (next, old) => {
  if (!next.includes(selected.value) || (old && next.at(-1) !== old.at(-1))) selected.value = next.at(-1) ?? ''
}, { immediate: true })
const photo = (view: ShapePhotoView) => shaping.photos.find(item => item.view === view && item.recorded_on === selected.value)
function askDelete(item: ShapePhoto): void { deleting.value = item; confirmOpen.value = true }
async function remove(): Promise<void> {
  if (!deleting.value) return
  const id = deleting.value.id
  confirmOpen.value = false
  try { notice.notify(await shaping.removePhoto(id), 'success') }
  catch (cause) { notice.notify(cause instanceof Error ? cause.message : '照片删除失败。', 'error') }
}
</script>

<template>
  <article class="panel shape-panel">
    <div class="panel-head"><div><p class="eyebrow">SAME YOU, DIFFERENT DAYS</p><h3>三视角对比照</h3></div><button class="text-button" :disabled="shaping.saving" @click="upload?.open(localDateString())">照片打卡</button></div>
    <p class="shape-muted">体重没有变化时，线条也可能在改变。每两周在相同条件下拍一次，照片和当日测量一起看。</p>
    <template v-if="dates.length">
      <div class="shape-photo-timeline" aria-label="照片时间线"><button v-for="date in dates" :key="date" class="button button-quiet" :aria-pressed="selected === date" @click="selected = date">{{ date }} <small>{{ shaping.photos.filter(item => item.recorded_on === date).length }}/3</small></button></div>
      <label v-if="dates.length > 1" class="shape-photo-slider">时间线 · {{ selected }}<input v-model.number="index" type="range" min="0" :max="dates.length - 1" step="1" :aria-valuetext="selected" /></label>
      <div class="shape-switches"><button class="button button-quiet" :aria-pressed="mode === 'period'" @click="mode = 'period'">同期三视角</button><button class="button button-quiet" :aria-pressed="mode === 'compare'" @click="mode = 'compare'">历史滑动对比</button></div>
      <template v-if="mode === 'period'">
        <div class="shape-photo-grid"><div v-for="angle in PHOTO_VIEWS" :key="angle" class="shape-photo-card"><h4>{{ PHOTO_LABELS[angle] }}</h4><img v-if="photo(angle)" :src="photoUrl(photo(angle)!)" :alt="`${selected}${PHOTO_LABELS[angle]}打卡照`" loading="lazy" /><div v-else class="shape-photo-missing">未记录此视角</div><div class="shape-photo-actions"><button class="text-button" :disabled="shaping.saving" @click="upload?.open(selected, angle)">{{ photo(angle) ? '替换' : '补充照片' }}</button><button v-if="photo(angle)" class="text-button shape-danger-text" :disabled="shaping.saving" @click="askDelete(photo(angle)!)">删除</button></div></div></div>
        <ShapeSnapshot :date="selected" />
      </template>
      <PhotoCompare v-else :date="selected" />
    </template>
    <div v-else class="shape-photo-empty"><p>还没有对比照，从正面、侧面、背面任意一个视角开始。</p><button class="button button-quiet" @click="upload?.open()">添加第一张照片</button></div>
    <PhotoUploadDialog ref="upload" />
    <ConfirmDialog v-model:open="confirmOpen" title="删除这张照片？" description="仅删除所选照片，测量数据和其他视角会保留。删除后无法恢复。" confirm-text="删除照片" danger @confirm="remove" />
  </article>
</template>
