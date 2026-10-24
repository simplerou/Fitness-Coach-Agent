/** Debounced search with explicit IME and lifecycle cancellation. */
export function createLiveSearch(
  run: (query: string) => void,
  invalidate: (query: string) => void,
  delay = 300,
) {
  let timer: ReturnType<typeof setTimeout> | null = null
  let composing = false
  let disposed = false
  let current = ''
  function cancel(): void {
    if (timer !== null) clearTimeout(timer)
    timer = null
  }
  function update(value: string): void {
    if (disposed) return
    current = value.trim()
    cancel()
    if (composing) return
    invalidate(current)
    if (!current) run('')
    else timer = setTimeout(() => { timer = null; if (!disposed) run(current) }, delay)
  }
  function flush(value: string): void {
    if (disposed || composing) return
    cancel(); current = value.trim(); invalidate(current); run(current)
  }
  function startComposition(): void {
    if (disposed) return
    composing = true; cancel(); invalidate(current)
  }
  function endComposition(value: string): void {
    composing = false; update(value)
  }
  function reset(): void { cancel(); composing = false; current = '' }
  function dispose(): void { reset(); disposed = true }
  return { update, flush, startComposition, endComposition, reset, dispose }
}
