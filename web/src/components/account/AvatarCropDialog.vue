<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useNotice } from '@/composables/useNotice'
import BaseDialog from '@/components/common/BaseDialog.vue'

const emit = defineEmits<{ saved: [dataUrl: string] }>()
const auth = useAuthStore()
const notice = useNotice()
const dialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const image = ref<HTMLImageElement | null>(null)
const sourceUrl = ref<string | null>(null)
const viewport = ref<HTMLElement | null>(null)
const percent = ref(68)
const frame = ref({ left: 0, top: 0, size: 0 })
const drag = ref<{ x: number; y: number; left: number; top: number } | null>(null)
const percentLabel = computed(() => `${percent.value}%`)

function openPicker(): void { fileInput.value?.click() }
function cleanup(): void {
  if (sourceUrl.value) URL.revokeObjectURL(sourceUrl.value)
  sourceUrl.value = null
  if (fileInput.value) fileInput.value.value = ''
  frame.value = { left: 0, top: 0, size: 0 }
}
function close(): void { dialog.value?.close(); cleanup() }
function fileChanged(event: Event): void {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) { notice.notify('请选择图片文件。', 'error'); cleanup(); return }
  if (file.size > 10 * 1024 * 1024) { notice.notify('图片不能超过 10 MB，请先压缩后再选择。', 'error'); cleanup(); return }
  cleanup()
  sourceUrl.value = URL.createObjectURL(file)
}
function initializeFrame(): void {
  if (!image.value || !viewport.value) return
  const imageRect = image.value.getBoundingClientRect()
  const viewportRect = viewport.value.getBoundingClientRect()
  const maxSide = Math.min(imageRect.width, imageRect.height)
  const size = maxSide * percent.value / 100
  frame.value = { left: imageRect.left - viewportRect.left + (imageRect.width - size) / 2, top: imageRect.top - viewportRect.top + (imageRect.height - size) / 2, size }
  dialog.value?.open()
}
function updatePercent(): void {
  if (!image.value || !viewport.value) return
  const imageRect = image.value.getBoundingClientRect()
  const viewportRect = viewport.value.getBoundingClientRect()
  const maxSide = Math.min(imageRect.width, imageRect.height)
  const size = maxSide * percent.value / 100
  const centerX = frame.value.left + frame.value.size / 2
  const centerY = frame.value.top + frame.value.size / 2
  frame.value = { left: Math.max(imageRect.left - viewportRect.left, Math.min(centerX - size / 2, imageRect.right - viewportRect.left - size)), top: Math.max(imageRect.top - viewportRect.top, Math.min(centerY - size / 2, imageRect.bottom - viewportRect.top - size)), size }
}
function startDrag(event: PointerEvent): void {
  drag.value = { x: event.clientX, y: event.clientY, left: frame.value.left, top: frame.value.top }
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  event.preventDefault()
}
function moveDrag(event: PointerEvent): void {
  if (!drag.value || !image.value || !viewport.value) return
  const imageRect = image.value.getBoundingClientRect()
  const viewportRect = viewport.value.getBoundingClientRect()
  frame.value.left = Math.max(imageRect.left - viewportRect.left, Math.min(drag.value.left + event.clientX - drag.value.x, imageRect.right - viewportRect.left - frame.value.size))
  frame.value.top = Math.max(imageRect.top - viewportRect.top, Math.min(drag.value.top + event.clientY - drag.value.y, imageRect.bottom - viewportRect.top - frame.value.size))
}
function save(): void {
  if (!image.value || !auth.user || !viewport.value) return
  const imageRect = image.value.getBoundingClientRect()
  const viewportRect = viewport.value.getBoundingClientRect()
  const scale = image.value.naturalWidth / imageRect.width
  const x = (frame.value.left - (imageRect.left - viewportRect.left)) * scale
  const y = (frame.value.top - (imageRect.top - viewportRect.top)) * scale
  const size = frame.value.size * scale
  const canvas = document.createElement('canvas')
  canvas.width = 320
  canvas.height = 320
  const context = canvas.getContext('2d')
  if (!context) { notice.notify('头像保存失败，请换一张较小的图片后重试。', 'error'); return }
  context.drawImage(image.value, x, y, size, size, 0, 0, 320, 320)
  const dataUrl = canvas.toDataURL('image/jpeg', 0.88)
  try {
    localStorage.setItem(`fitnessCoachAvatar:${auth.user.id}`, dataUrl)
    emit('saved', dataUrl)
    close()
    notice.notify('头像已更新。', 'success')
  } catch { notice.notify('头像保存失败，请换一张较小的图片后重试。', 'error') }
}

watch(sourceUrl, (url) => { if (!url) return })
defineExpose({ openPicker })
</script>

<template>
  <input ref="fileInput" class="hidden" type="file" accept="image/jpeg,image/png,image/webp,image/gif" @change="fileChanged" />
  <BaseDialog ref="dialog" class="user-dialog avatar-crop-dialog" aria-labelledby="avatar-crop-title" @close="cleanup">
    <div class="user-dialog-top"><div><p class="eyebrow">PROFILE PHOTO</p><h2 id="avatar-crop-title">调整头像区域</h2></div><button class="user-dialog-close" type="button" aria-label="关闭头像裁剪" @click="close">×</button></div>
    <p class="avatar-crop-help">拖动方框选择要保留的区域，使用下方滑块调整裁剪范围。</p>
    <div ref="viewport" class="avatar-crop-viewport"><img v-if="sourceUrl" ref="image" :src="sourceUrl" alt="待裁剪的头像图片" @load="initializeFrame" /><div class="avatar-crop-selection" :style="{ width: `${frame.size}px`, height: `${frame.size}px`, left: `${frame.left}px`, top: `${frame.top}px` }" role="img" aria-label="可拖动的正方形头像选区" @pointerdown="startDrag" @pointermove="moveDrag" @pointerup="drag = null" @pointercancel="drag = null"><span></span></div></div>
    <label class="avatar-zoom-control"><span>裁剪范围</span><input v-model.number="percent" type="range" min="35" max="95" @input="updatePercent" /><span>{{ percentLabel }}</span></label>
    <div class="account-dialog-actions avatar-crop-actions"><button class="button button-quiet" type="button" @click="close">取消</button><button class="button button-primary" type="button" @click="save">使用此头像</button></div>
  </BaseDialog>
</template>
