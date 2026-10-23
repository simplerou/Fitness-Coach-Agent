<script setup lang="ts">
import { ref, useAttrs } from 'vue'

defineOptions({ inheritAttrs: false })
const props = withDefaults(defineProps<{ dismissible?: boolean }>(), { dismissible: true })
const emit = defineEmits<{ close: [] }>()
const attrs = useAttrs()
const element = ref<HTMLDialogElement | null>(null)
function open(): void { if (element.value && !element.value.open) element.value.showModal() }
function close(): void { if (element.value?.open) element.value.close() }
function handleClose(): void { emit('close') }
function dismiss(): void { if (props.dismissible) close() }
function cancel(event: Event): void { if (!props.dismissible) event.preventDefault() }
defineExpose({ open, close, element })
</script>

<template>
  <dialog ref="element" v-bind="attrs" @close="handleClose" @click.self="dismiss" @cancel="cancel">
    <slot />
  </dialog>
</template>
