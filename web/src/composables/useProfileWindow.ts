import { ref } from 'vue'

const open = ref(false)

export function useProfileWindow() {
  function openProfileWindow(): void { open.value = true }
  function closeProfileWindow(): void { open.value = false }
  return { open, openProfileWindow, closeProfileWindow }
}
