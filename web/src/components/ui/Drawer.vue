<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{ open: boolean; title: string }>()
const emit = defineEmits<{ close: [] }>()
const panel = ref<HTMLElement | null>(null)
let previous: HTMLElement | null = null

function keydown(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
  if (event.key !== 'Tab' || !panel.value) return
  const list = [...panel.value.querySelectorAll<HTMLElement>('button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])')]
    .filter((element) => !element.hasAttribute('disabled'))
  if (!list.length) return
  const first = list[0]
  const last = list.at(-1)!
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
}

watch(() => props.open, async (open) => {
  if (open) {
    previous = document.activeElement as HTMLElement
    document.addEventListener('keydown', keydown)
    await nextTick()
    panel.value?.querySelector<HTMLElement>('button,[href],input,select,textarea,[tabindex]')?.focus()
  } else {
    document.removeEventListener('keydown', keydown)
    previous?.focus()
  }
}, { immediate: true })
onBeforeUnmount(() => document.removeEventListener('keydown', keydown))
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="drawer-layer">
      <button class="drawer-backdrop" aria-label="关闭抽屉" @click="$emit('close')" />
      <aside ref="panel" class="app-drawer" role="dialog" aria-modal="true" :aria-label="title">
        <header><h2>{{ title }}</h2><button class="drawer-close" aria-label="关闭" @click="$emit('close')">×</button></header>
        <div class="drawer-body"><slot /></div>
      </aside>
    </div>
  </Teleport>
</template>
