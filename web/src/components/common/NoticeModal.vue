<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useNotice } from '@/composables/useNotice'
import BaseDialog from '@/components/common/BaseDialog.vue'

const notice = useNotice()
const { kind, message } = notice
const dialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const title = ref<HTMLElement | null>(null)

watch(notice.visible, async (visible) => {
  await nextTick()
  if (visible && dialog.value) {
    dialog.value.open()
    title.value?.focus()
  } else if (!visible) {
    dialog.value?.close()
  }
})

function close(): void {
  notice.close()
}
</script>

<template>
  <BaseDialog ref="dialog" class="notice-dialog" @close="close">
    <article class="alert-modal" :data-kind="kind">
      <span class="alert-modal-icon" aria-hidden="true">{{ kind === 'error' ? '!' : 'i' }}</span>
      <h2 ref="title" tabindex="-1">{{ kind === 'error' ? '请检查一下' : '提示' }}</h2>
      <p role="alert" aria-live="assertive">{{ message }}</p>
      <button class="button button-primary" type="button" @click="close">知道了</button>
    </article>
  </BaseDialog>
</template>
