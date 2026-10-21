<script setup lang="ts">
import { computed, ref } from 'vue'
import BaseDialog from '@/components/common/BaseDialog.vue'
import { PHOTO_VIEWS, PHOTO_LABELS } from '@/constants/shaping'
import { useShapingStore } from '@/stores/shaping'
import { prepareShapePhoto } from '@/utils/shaping'
import { localDateString } from '@/utils/date'
import { useNotice } from '@/composables/useNotice'
import type { ShapePhotoView } from '@/api/types'
import FilterSelect from '@/components/ui/FilterSelect.vue'
const shaping = useShapingStore()
const notice = useNotice()
const dialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const input = ref<HTMLInputElement | null>(null)
const date = ref(localDateString())
const view = ref<ShapePhotoView>('front')
const viewValue = computed({ get: () => view.value, set: (value: string) => { view.value = value as ShapePhotoView } })
const viewOptions = PHOTO_VIEWS.map(angle => ({ value: angle, label: PHOTO_LABELS[angle] }))
const preview = ref('')
const error = ref('')
const processing = ref(false)
let selection = 0
function reset(): void { selection++; preview.value = ''; error.value = ''; processing.value = false; if (input.value) input.value.value = '' }
function open(day = localDateString(), angle: ShapePhotoView = 'front'): void { reset(); date.value = day; view.value = angle; dialog.value?.open() }
async function choose(event: Event): Promise<void> {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  const version = ++selection
  preview.value = ''
  error.value = ''
  processing.value = true
  try { const image = await prepareShapePhoto(file); if (version === selection) preview.value = image }
  catch (cause) { if (version === selection) error.value = cause instanceof Error ? cause.message : '图片无法读取，请重新选择。' }
  finally { if (version === selection) processing.value = false }
}
async function save(): Promise<void> {
  if (!preview.value || processing.value) return
  try {
    const message = await shaping.savePhoto(date.value, view.value, preview.value)
    dialog.value?.close()
    notice.notify(message, 'success')
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '照片保存失败。' }
}
defineExpose({ open })
</script>

<template>
  <BaseDialog ref="dialog" class="user-dialog shape-photo-dialog" aria-labelledby="shape-photo-title" @close="reset">
    <div class="user-dialog-top"><div><p class="eyebrow">PHOTO CHECK-IN</p><h2 id="shape-photo-title">三视角照片打卡</h2></div><button class="user-dialog-close" :disabled="shaping.saving" aria-label="关闭照片窗口" @click="dialog?.close()">×</button></div>
    <p class="shape-muted">尽量固定距离、光线、衣着和自然站姿，拍到全身。同一天同一视角再次保存会替换原图，可逐张补齐三个视角。</p>
    <form class="form-stack" @submit.prevent="save"><div class="field-row"><label class="field"><span>拍摄日期</span><input v-model="date" type="date" :max="localDateString()" required :disabled="shaping.saving" /></label><label class="field"><span>视角</span><FilterSelect v-model="viewValue" :options="viewOptions" aria-label="视角" :disabled="shaping.saving" /></label></div>
      <label class="field"><span>选择照片（JPG / PNG / WebP）</span><input ref="input" type="file" accept="image/jpeg,image/png,image/webp" :disabled="processing || shaping.saving" @change="choose" /></label>
      <p v-if="processing" role="status">正在处理照片…</p><img v-if="preview" class="shape-upload-preview" :src="preview" :alt="`${PHOTO_LABELS[view]}待保存照片`" />
      <p v-if="shaping.photos.some(photo => photo.recorded_on === date && photo.view === view)" class="shape-warning">这一天已有{{ PHOTO_LABELS[view] }}照片，保存后会替换。</p><p v-if="error" class="shape-error" role="alert">{{ error }}</p>
      <p class="fine-print">照片压缩后保存到本机数据库，移除 EXIF 信息，仅当前账号可通过接口访问，不发送给饮食 AI。当前演示版数据库未做应用层加密，请自行决定是否上传。</p>
      <div class="shape-actions"><button class="button button-quiet" type="button" :disabled="shaping.saving" @click="dialog?.close()">取消</button><button class="button button-primary" :disabled="!preview || processing || shaping.saving">{{ shaping.saving ? '正在保存…' : '保存照片' }}</button></div>
    </form>
  </BaseDialog>
</template>
