import { ref } from 'vue'

export type NoticeKind = 'info' | 'success' | 'error'
const message = ref('')
const kind = ref<NoticeKind>('info')
const visible = ref(false)
let returnFocus: HTMLElement | null = null

export function useNotice() {
  function notify(nextMessage: string, nextKind: NoticeKind = 'info'): void {
    if (!visible.value) returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    message.value = nextMessage
    kind.value = nextKind
    visible.value = true
  }

  function close(): void {
    visible.value = false
    returnFocus?.focus()
    returnFocus = null
  }

  return { message, kind, visible, notify, close }
}
