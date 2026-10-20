<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import BaseDialog from '@/components/common/BaseDialog.vue'
import type { ExerciseDefinition } from '@/api/types'

const props = defineProps<{ exercise: ExerciseDefinition | null }>()
const emit = defineEmits<{ close: [] }>()
const dialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const imageIndex = ref(0)
const autoplay = ref(true)
const videoFailed = ref(false)
const failedImages = ref<Set<string>>(new Set())
let autoplayTimer: number | null = null

const availableImages = computed(() =>
  (props.exercise?.demo_images ?? []).filter((url) => !failedImages.value.has(url)),
)
const activeImage = computed(() => availableImages.value[imageIndex.value] ?? null)
const hasVideo = computed(() => Boolean(props.exercise?.demo_video_url) && !videoFailed.value)

function stopAutoplay(): void {
  if (autoplayTimer !== null) window.clearInterval(autoplayTimer)
  autoplayTimer = null
}

function startAutoplay(): void {
  stopAutoplay()
  if (!autoplay.value || hasVideo.value || availableImages.value.length < 2) return
  autoplayTimer = window.setInterval(() => {
    imageIndex.value = (imageIndex.value + 1) % availableImages.value.length
  }, 1600)
}

function selectImage(index: number): void {
  imageIndex.value = index
  startAutoplay()
}

function toggleAutoplay(): void {
  autoplay.value = !autoplay.value
  startAutoplay()
}

function markImageFailed(url: string): void {
  failedImages.value = new Set([...failedImages.value, url])
  imageIndex.value = 0
  startAutoplay()
}

function handleClose(): void {
  stopAutoplay()
  emit('close')
}

watch(() => props.exercise, async (value) => {
  stopAutoplay()
  imageIndex.value = 0
  autoplay.value = true
  videoFailed.value = false
  failedImages.value = new Set()
  if (!value) {
    dialog.value?.close()
    return
  }
  await nextTick()
  dialog.value?.open()
  startAutoplay()
})

watch(() => availableImages.value.length, startAutoplay)
onBeforeUnmount(stopAutoplay)
</script>

<template>
  <BaseDialog ref="dialog" class="user-dialog exercise-detail-dialog" @close="handleClose">
    <div v-if="exercise" class="dialog-card">
      <div class="user-dialog-top">
        <div><p class="eyebrow">EXERCISE GUIDE</p><h2>{{ exercise.name }}</h2></div>
        <button class="dialog-close" type="button" aria-label="关闭动作详情" @click="dialog?.close()">×</button>
      </div>
      <div class="exercise-tags">
        <span>{{ exercise.category }}</span><span v-for="muscle in exercise.target_muscles" :key="muscle">{{ muscle }}</span>
      </div>

      <section class="exercise-media-section">
        <div class="exercise-media-heading">
          <div><p class="eyebrow">DEMONSTRATION</p><h3>动作示范</h3></div>
          <span v-if="!hasVideo && availableImages.length > 1">起始与结束动作自动切换</span>
        </div>
        <video
          v-if="hasVideo"
          class="exercise-demo-video"
          :src="exercise.demo_video_url ?? undefined"
          :poster="availableImages[0]"
          controls
          playsinline
          preload="metadata"
          @error="videoFailed = true"
        >当前浏览器无法播放该动作视频。</video>
        <div v-else-if="activeImage" class="exercise-demo-gallery">
          <div class="exercise-demo-stage">
            <img
              :src="activeImage"
              :alt="`${exercise.name}${imageIndex === 0 ? '起始' : '结束'}动作示范`"
              loading="eager"
              referrerpolicy="no-referrer"
              @error="markImageFailed(activeImage)"
            >
            <span>{{ imageIndex === 0 ? '起始动作' : '结束动作' }}</span>
          </div>
          <div class="exercise-demo-controls">
            <button
              v-for="(_, index) in availableImages"
              :key="index"
              type="button"
              :class="{ active: imageIndex === index }"
              :aria-pressed="imageIndex === index"
              @click="selectImage(index)"
            >{{ index === 0 ? '起始' : '结束' }}</button>
            <button v-if="availableImages.length > 1" type="button" :aria-pressed="autoplay" @click="toggleAutoplay">
              {{ autoplay ? '暂停演示' : '播放演示' }}
            </button>
          </div>
        </div>
        <div v-else class="exercise-media-empty">
          <b>当前动作暂无匹配的演示媒体</b>
          <p>请先按照下方文字要领完成动作，不使用相似动作图片代替。</p>
        </div>
        <p v-if="exercise.media_credit" class="exercise-media-credit">
          素材：
          <a v-if="exercise.media_source_url" :href="exercise.media_source_url" target="_blank" rel="noopener noreferrer">
            {{ exercise.media_credit }}
          </a>
          <template v-else>{{ exercise.media_credit }}</template>
          <span v-if="exercise.media_license"> · {{ exercise.media_license }}</span>
        </p>
      </section>

      <section><h3>动作要领</h3><ul><li v-for="cue in exercise.cues" :key="cue">{{ cue }}</li></ul></section>
      <section><h3>常见错误与修正</h3><article v-for="item in exercise.common_errors" :key="item.error"><b>{{ item.error }}</b><p>{{ item.correction }}</p></article></section>
      <div class="exercise-variants"><section><h3>退阶</h3><p>{{ exercise.regressions.join('、') || '暂无' }}</p></section><section><h3>进阶</h3><p>{{ exercise.progressions.join('、') || '暂无' }}</p></section></div>
      <section><h3>同目标肌群替代动作</h3><p v-for="item in exercise.alternatives" :key="item.name"><b>{{ item.name }}</b> · {{ item.scene }}</p></section>
      <p class="fine-print">动作应在无痛、可控制的范围内完成。出现关节疼痛、锐痛或肿胀时停止该动作。</p>
    </div>
  </BaseDialog>
</template>
