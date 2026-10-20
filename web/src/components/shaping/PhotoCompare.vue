<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useShapingStore } from '@/stores/shaping'
import { PHOTO_VIEWS, PHOTO_LABELS } from '@/constants/shaping'
import { photoUrl } from '@/utils/shaping'
import type { ShapePhotoView } from '@/api/types'
import ShapeSnapshot from './ShapeSnapshot.vue'
const props = defineProps<{ date: string }>()
const shaping = useShapingStore()
const angle = ref<ShapePhotoView>('front')
const beforeDate = ref('')
const slider = ref(50)
const dragging = ref(false)
const dates = computed(() => [...new Set(shaping.photos.filter(photo => photo.view === angle.value).map(photo => photo.recorded_on))].sort())
const before = computed(() => shaping.photos.find(photo => photo.view === angle.value && photo.recorded_on === beforeDate.value))
const after = computed(() => shaping.photos.find(photo => photo.view === angle.value && photo.recorded_on === props.date))
watch([dates, () => props.date], () => {
  if (!dates.value.includes(beforeDate.value) || beforeDate.value >= props.date) beforeDate.value = dates.value.find(date => date < props.date) ?? ''
  slider.value = 50
}, { immediate: true })
function moveDivider(event: PointerEvent): void {
  if (!dragging.value) return
  const bounds = (event.currentTarget as HTMLElement).getBoundingClientRect()
  slider.value = Math.round(Math.max(0, Math.min(100, (event.clientX - bounds.left) / bounds.width * 100)))
}
function startDrag(event: PointerEvent): void {
  if (!event.isPrimary || event.button !== 0) return
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  dragging.value = true
  moveDivider(event)
}
</script>

<template>
  <div class="shape-photo-compare">
    <div class="shape-compare-controls"><label class="field"><span>对比视角</span><select v-model="angle"><option v-for="view in PHOTO_VIEWS" :key="view" :value="view">{{ PHOTO_LABELS[view] }}</option></select></label><label class="field"><span>之前的日期</span><select v-model="beforeDate"><option value="">请选择更早记录</option><option v-for="date in dates.filter(day => day < props.date)" :key="date" :value="date">{{ date }}</option></select></label><div class="shape-muted">当前对比：{{ date || '未选择日期' }}</div></div>
    <template v-if="before && after && beforeDate !== date">
      <div class="shape-comparison-frame" @pointerdown="startDrag" @pointermove="moveDivider" @pointerup="dragging = false" @pointercancel="dragging = false" @lostpointercapture="dragging = false"><img :src="photoUrl(after)" :alt="`${date}${PHOTO_LABELS[angle]}`" draggable="false" /><img class="shape-comparison-before" :src="photoUrl(before)" :style="{ clipPath: `inset(0 ${100 - slider}% 0 0)` }" :alt="`${beforeDate}${PHOTO_LABELS[angle]}`" draggable="false" /><span class="shape-comparison-divider" :style="{ left: `${slider}%` }" /><div class="shape-comparison-labels"><span>之前 {{ beforeDate }}</span><span>之后 {{ date }}</span></div></div>
      <label class="shape-photo-slider">滑动比较同一视角<input v-model.number="slider" type="range" min="0" max="100" :aria-valuetext="`之前照片显示 ${slider}%`" /></label>
      <div class="shape-snapshot-pair"><ShapeSnapshot :date="beforeDate" /><ShapeSnapshot :date="date" /></div>
      <p class="fine-print">照片按原比例居中显示；拍摄距离、姿势和光线可能影响视觉判断，请同时参考同日实测数据。</p>
    </template>
    <p v-else class="shape-muted">需要当前日期和更早日期的同一视角照片才能滑动对比。可切换视角或补充照片，缺失视角不会用其他照片代替。</p>
  </div>
</template>
