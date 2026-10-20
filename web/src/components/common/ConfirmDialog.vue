<script setup lang="ts">
import { ref, watch } from 'vue'
import BaseDialog from '@/components/common/BaseDialog.vue'

const props = defineProps<{ open: boolean; title: string; description: string; confirmText?: string; danger?: boolean }>()
const emit = defineEmits<{ 'update:open': [open: boolean]; confirm: [] }>()
const dialog = ref<InstanceType<typeof BaseDialog> | null>(null)
watch(() => props.open, (open) => open ? dialog.value?.open() : dialog.value?.close(), { immediate: true })
function close(): void { emit('update:open', false) }
</script>

<template>
  <BaseDialog ref="dialog" class="confirm-dialog" @close="close">
    <article class="alert-modal" role="alertdialog" aria-modal="true">
      <span class="alert-modal-icon" aria-hidden="true">{{ danger ? '!' : 'i' }}</span>
      <h2>{{ title }}</h2><p>{{ description }}</p>
      <div class="confirm-modal-actions"><button class="button button-quiet" type="button" @click="close">取消</button><button class="button" :class="danger ? 'button-danger' : 'button-primary'" type="button" @click="emit('confirm')">{{ confirmText || '确认' }}</button></div>
    </article>
  </BaseDialog>
</template>
