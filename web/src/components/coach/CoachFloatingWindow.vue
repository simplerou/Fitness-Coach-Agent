<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useShapingIntelligenceStore } from '@/stores/shapingIntelligence'
import { useCoachWindow } from '@/composables/useCoachWindow'
import { exerciseNameLabel } from '@/utils/exerciseLabels'
import type { CoachAnswerResponse } from '@/api/types'

type ChatEntry = { id: number; question: string; response: CoachAnswerResponse }
type DockSide = 'left' | 'right' | 'top' | 'bottom'

const intelligence = useShapingIntelligenceStore()
const route = useRoute()
const coach = useCoachWindow()
const panel = ref<HTMLElement | null>(null)
const launcher = ref<HTMLButtonElement | null>(null)
const edgeTab = ref<HTMLButtonElement | null>(null)
const textarea = ref<HTMLTextAreaElement | null>(null)
const question = ref('')
const consent = ref(false)
const collapsed = ref(false)
const launcherCollapsed = ref(false)
const dockSide = ref<DockSide>('right')
const edgePosition = ref({ x: window.innerWidth - 48, y: Math.round(window.innerHeight * 0.48) })
const position = ref<{ x: number; y: number } | null>(null)
const launcherPosition = ref<{ x: number; y: number } | null>(null)
const messages = ref<ChatEntry[]>([])
const error = ref('')
let messageId = 0
let dragOffset = { x: 0, y: 0 }
let dragOrigin = { x: 0, y: 0 }
let dragging = false
let draggingLauncher = false
let draggingFromEdge = false
let edgeDragReady = true
let edgeExpandedByDrag = false
let movedDuringDrag = false
let suppressLauncherClick = false
let lastPointer = { x: 0, y: 0 }

const pageLabels: Record<string, string> = { today:'概览',plan:'周计划',log:'训练记录',diet:'饮食',shaping:'效果报告',review:'周回顾',library:'动作库',profile:'设置' }
const contextLabel = computed(() => pageLabels[String(route.name)] || '当前页面')
const transformOrigin = computed(() => dockSide.value === 'left' ? 'left center' : dockSide.value === 'right' ? 'right center' : dockSide.value === 'top' ? 'center top' : 'center bottom')
const panelStyle = computed(() => position.value ? { left:`${position.value.x}px`,top:`${position.value.y}px`,right:'auto',bottom:'auto',transformOrigin:transformOrigin.value } : undefined)
const launcherStyle = computed(() => launcherPosition.value ? { left:`${launcherPosition.value.x}px`,top:`${launcherPosition.value.y}px`,right:'auto',bottom:'auto',transformOrigin:transformOrigin.value } : { transformOrigin:transformOrigin.value })
const edgeTabStyle = computed(() => ({ left:`${edgePosition.value.x}px`,top:`${edgePosition.value.y}px`,right:'auto',bottom:'auto',transformOrigin:transformOrigin.value }))
const examples = ['俯卧撑怎么呼吸和发力？','器械被占用时怎样选择替代动作？','结合我的本周计划，训练该怎么安排？']

watch(() => coach.suggestedQuestion.value, (value) => {
  if (value) { question.value = value; coach.suggestedQuestion.value = ''; void focusQuestion() }
})
watch(() => coach.open.value, (value) => { if (value) { collapsed.value = false; placePanelNearLauncher(); void focusQuestion() } })
watch(() => route.fullPath, () => {
  if (route.query.section === 'coach') coach.openCoach()
})

async function focusQuestion(): Promise<void> { await nextTick(); textarea.value?.focus() }
async function submit(): Promise<void> {
  const value = question.value.trim()
  if (!value || intelligence.asking) return
  error.value = ''
  try {
    await intelligence.ask(value, consent.value)
    if (intelligence.coachAnswer) messages.value.push({ id:++messageId, question:value, response:intelligence.coachAnswer })
    question.value = ''
    await nextTick()
    panel.value?.querySelector('.coach-conversation')?.scrollTo({ top:10_000, behavior:'smooth' })
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '教练问答暂时不可用。' }
}
function useExample(value: string): void { question.value = value; void focusQuestion() }
function collapse(): void {
  const rect = panel.value?.getBoundingClientRect()
  if (!rect || !panel.value) return
  setEdgePosition(rect, Number.POSITIVE_INFINITY)
  const currentPanel = panel.value
  void (async () => {
    await animateIntoDock(currentPanel)
    collapsed.value = true
    await nextTick()
    if (edgeTab.value) await animateFromDock(edgeTab.value)
  })()
}
function expand(): void {
  collapsed.value = false
  const width = Math.min(430, window.innerWidth - 32)
  const height = Math.min(650, window.innerHeight - 96)
  position.value = { x:Math.max(0,Math.min(window.innerWidth - width,edgePosition.value.x)), y:Math.max(64,Math.min(window.innerHeight - height,edgePosition.value.y)) }
  void focusQuestion()
  void nextTick(async () => { if (panel.value) await animateFromDock(panel.value) })
}
function expandLauncher(): void {
  launcherCollapsed.value = false
  const width = Math.min(184,window.innerWidth - 16)
  launcherPosition.value = { x:Math.max(0,Math.min(window.innerWidth - width,edgePosition.value.x)), y:Math.max(0,Math.min(window.innerHeight - 56,edgePosition.value.y)) }
  void nextTick(async () => { if (launcher.value) await animateFromDock(launcher.value) })
}
function placePanelNearLauncher(): void {
  const anchor = launcher.value ?? edgeTab.value
  const rect = anchor?.getBoundingClientRect()
  const width = Math.min(430,window.innerWidth-32)
  const height = Math.min(650,window.innerHeight-96)
  if (!rect) {
    if (!position.value) position.value = { x:Math.max(16,window.innerWidth-width-24),y:Math.max(64,window.innerHeight-height-24) }
    return
  }
  const x = Math.max(0,Math.min(window.innerWidth-width,rect.left+rect.width/2-width/2))
  const above = rect.top-height-12
  const below = rect.bottom+12
  const y = above >= 64 ? above : below+height <= window.innerHeight ? below : Math.max(64,Math.min(window.innerHeight-height,rect.top-height/2))
  position.value = { x,y }
}
function closeCoachFromPanel(): void {
  const rect = panel.value?.getBoundingClientRect()
  if (rect) {
    const width = Math.min(184,window.innerWidth-16)
    const height = 56
    launcherPosition.value = { x:Math.max(0,Math.min(window.innerWidth-width,rect.right-width)),y:Math.max(0,Math.min(window.innerHeight-height,rect.bottom-height)) }
  }
  coach.closeCoach()
}
function setEdgePosition(rect: DOMRect, threshold: number): boolean {
  const candidates = [
    { side:'left' as const,distance:rect.left,x:0,y:rect.top+(rect.height-58)/2 },
    { side:'right' as const,distance:window.innerWidth-rect.right,x:window.innerWidth-48,y:rect.top+(rect.height-58)/2 },
    { side:'top' as const,distance:rect.top,x:rect.left+(rect.width-48)/2,y:0 },
    { side:'bottom' as const,distance:window.innerHeight-rect.bottom,x:rect.left+(rect.width-48)/2,y:window.innerHeight-58 },
  ].sort((a,b)=>a.distance-b.distance)
  const nearest = candidates[0]
  if (!nearest || nearest.distance > threshold) return false
  dockSide.value = nearest.side
  edgePosition.value = { x:Math.max(0,Math.min(window.innerWidth-48,nearest.x)),y:Math.max(0,Math.min(window.innerHeight-58,nearest.y)) }
  return true
}
function startDrag(event: MouseEvent, source: 'panel' | 'launcher' = 'panel'): void {
  const target = event.target
  if (window.innerWidth < 768 || (source === 'panel' && target instanceof Element && target.closest('button'))) return
  const element = source === 'launcher' ? launcher.value : panel.value
  const rect = element?.getBoundingClientRect()
  if (!rect) return
  event.preventDefault()
  dragging = true
  draggingLauncher = source === 'launcher'
  draggingFromEdge = false
  edgeDragReady = true
  movedDuringDrag = false
  dragOrigin = { x:event.clientX,y:event.clientY }
  lastPointer = { ...dragOrigin }
  dragOffset = { x:event.clientX-rect.left,y:event.clientY-rect.top }
  if (draggingLauncher) launcherPosition.value = { x:rect.left,y:rect.top }
  else position.value = { x:rect.left,y:rect.top }
  window.addEventListener('mousemove', move, true)
  window.addEventListener('mouseup', endDrag, true)
}
function startEdgeDrag(event: MouseEvent): void {
  if (window.innerWidth < 768) return
  event.preventDefault()
  dragging = true
  draggingFromEdge = true
  edgeDragReady = true
  edgeExpandedByDrag = false
  draggingLauncher = !coach.open.value
  movedDuringDrag = false
  dragOrigin = { x:event.clientX,y:event.clientY }
  lastPointer = { ...dragOrigin }
  window.addEventListener('mousemove',move,true)
  window.addEventListener('mouseup',endDrag,true)
}
function move(event: MouseEvent): void {
  if (!dragging) return
  lastPointer = { x:event.clientX,y:event.clientY }
  if (Math.abs(event.clientX-dragOrigin.x) + Math.abs(event.clientY-dragOrigin.y) > 4) movedDuringDrag = true
  if (draggingFromEdge && !edgeExpandedByDrag) {
    if (!movedDuringDrag) return
    edgeExpandedByDrag = true
    edgeDragReady = false
    if (draggingLauncher) {
      launcherCollapsed.value = false
      const width = Math.min(184,window.innerWidth-16)
      launcherPosition.value = { x:Math.max(0,Math.min(window.innerWidth-width,edgePosition.value.x)),y:Math.max(0,Math.min(window.innerHeight-56,edgePosition.value.y)) }
    } else {
      collapsed.value = false
      const width = Math.min(430,window.innerWidth-32)
      const height = Math.min(650,window.innerHeight-96)
      position.value = { x:Math.max(0,Math.min(window.innerWidth-width,edgePosition.value.x)),y:Math.max(64,Math.min(window.innerHeight-height,edgePosition.value.y)) }
    }
    void nextTick(async () => {
      const element = draggingLauncher ? launcher.value : panel.value
      if (!dragging || !element) return
      await animateFromDock(element)
      if (!dragging) return
      const rect = element.getBoundingClientRect()
      dragOffset = { x:lastPointer.x-rect.left,y:lastPointer.y-rect.top }
      edgeDragReady = true
    })
    return
  }
  if (!edgeDragReady) return
  const element = draggingLauncher ? launcher.value : panel.value
  if (!element) return
  const rect = element.getBoundingClientRect()
  const nextPosition = { x:Math.max(0,Math.min(window.innerWidth-rect.width,event.clientX-dragOffset.x)), y:Math.max(0,Math.min(window.innerHeight-rect.height,event.clientY-dragOffset.y)) }
  if (draggingLauncher) launcherPosition.value = nextPosition
  else position.value = { x:nextPosition.x,y:Math.max(64,Math.min(window.innerHeight-80,event.clientY-dragOffset.y)) }
}
function shouldAnimateMorph(): boolean { return !window.matchMedia('(prefers-reduced-motion: reduce)').matches }
async function animateFromDock(element: HTMLElement): Promise<void> {
  if (!shouldAnimateMorph()) return
  const animation = element.animate([{ transform:'scale(.12)',opacity:0 },{ transform:'scale(1)',opacity:1 }],{ duration:600,easing:'cubic-bezier(.2,.8,.2,1)' })
  await animation.finished.catch(() => undefined)
}
async function animateIntoDock(element: HTMLElement): Promise<void> {
  if (!shouldAnimateMorph()) return
  const animation = element.animate([{ transform:'scale(1)',opacity:1 },{ transform:'scale(.12)',opacity:0 }],{ duration:560,easing:'cubic-bezier(.4,0,.8,.2)' })
  await animation.finished.catch(() => undefined)
}
function endDrag(): void {
  if (draggingLauncher && movedDuringDrag) {
    suppressLauncherClick = true
    window.setTimeout(() => { suppressLauncherClick = false }, 0)
  }
  const wasDraggingLauncher = draggingLauncher
  const wasDraggingFromEdge = draggingFromEdge
  dragging = false
  draggingLauncher = false
  draggingFromEdge = false
  edgeDragReady = true
  edgeExpandedByDrag = false
  window.removeEventListener('mousemove',move, true)
  window.removeEventListener('mouseup',endDrag, true)
  if (wasDraggingLauncher) {
    if (movedDuringDrag && launcher.value && setEdgePosition(launcher.value.getBoundingClientRect(),wasDraggingFromEdge?20:64)) {
      const currentLauncher = launcher.value
      void (async () => {
        await animateIntoDock(currentLauncher)
        launcherCollapsed.value=true
        await nextTick()
        if (edgeTab.value) await animateFromDock(edgeTab.value)
      })()
    }
    return
  }
  if (!panel.value || !position.value) return
  if (setEdgePosition(panel.value.getBoundingClientRect(),wasDraggingFromEdge?20:96)) {
    const currentPanel = panel.value
    void (async () => {
      await animateIntoDock(currentPanel)
      collapsed.value=true
      await nextTick()
      if (edgeTab.value) await animateFromDock(edgeTab.value)
    })()
  }
}
function openFromLauncher(): void {
  if (suppressLauncherClick) { suppressLauncherClick = false; return }
  coach.openCoach()
}
function expandEdgeFromKeyboard(): void {
  if (coach.open.value) expand()
  else expandLauncher()
}
function keydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && coach.open.value) closeCoachFromPanel()
  if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 'k') { event.preventDefault();coach.openCoach() }
}
onMounted(() => { document.addEventListener('keydown',keydown); if (route.query.section === 'coach') coach.openCoach() })
onBeforeUnmount(() => { document.removeEventListener('keydown',keydown);window.removeEventListener('mousemove',move, true);window.removeEventListener('mouseup',endDrag, true) })
</script>

<template>
  <Teleport to="body">
    <button v-if="!coach.open.value && !launcherCollapsed" key="coach-launcher" ref="launcher" class="coach-launcher" :style="launcherStyle" type="button" aria-label="打开 AI 教练" title="拖动移动，点击打开" @mousedown="startDrag($event, 'launcher')" @click="openFromLauncher">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a7 7 0 0 0-7 7v3a4 4 0 0 0 4 4h1l2.8 2.5c.5.4 1.2.1 1.2-.5v-2h1a4 4 0 0 0 4-4v-3a7 7 0 0 0-7-7Z"/><path d="M9 10h.01M15 10h.01M9.5 13.5c1.5 1 3.5 1 5 0"/></svg><span>AI 教练</span>
    </button>
    <button v-else-if="collapsed || (!coach.open.value && launcherCollapsed)" key="coach-edge-tab" ref="edgeTab" class="coach-edge-tab" :class="`is-${dockSide}`" :style="edgeTabStyle" type="button" :aria-label="coach.open.value ? '按住并拖动展开 AI 教练窗口' : '按住并拖动展开 AI 教练按钮'" @mousedown="startEdgeDrag" @keydown.enter.prevent="expandEdgeFromKeyboard" @keydown.space.prevent="expandEdgeFromKeyboard">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a7 7 0 0 0-7 7v3a4 4 0 0 0 4 4h1l2.8 2.5c.5.4 1.2.1 1.2-.5v-2h1a4 4 0 0 0 4-4v-3a7 7 0 0 0-7-7Z"/><path d="M9 10h.01M15 10h.01"/></svg>
    </button>
    <aside v-else-if="coach.open.value" key="coach-panel" ref="panel" class="coach-floating-window" :style="panelStyle" role="dialog" aria-label="AI 教练问答" aria-modal="false">
      <header class="coach-window-header" @mousedown="startDrag">
        <div class="coach-window-title"><span class="coach-window-drag-handle" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 5h.01M16 5h.01M8 12h.01M16 12h.01M8 19h.01M16 19h.01"/></svg></span><span class="coach-window-avatar"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a7 7 0 0 0-7 7v3a4 4 0 0 0 4 4h1l2.8 2.5c.5.4 1.2.1 1.2-.5v-2h1a4 4 0 0 0 4-4v-3a7 7 0 0 0-7-7Z"/></svg></span><div><b>AI 教练</b><small>{{ contextLabel }}上下文 · 动作资料检索</small></div></div>
        <div class="coach-window-actions"><button type="button" title="缩进页面边缘" aria-label="缩进页面边缘" @click="collapse"><svg viewBox="0 0 20 20"><path d="M5 10h10"/></svg></button><button type="button" title="关闭" aria-label="关闭 AI 教练" @click="closeCoachFromPanel"><svg viewBox="0 0 20 20"><path d="m6 6 8 8m0-8-8 8"/></svg></button></div>
      </header>
      <div class="coach-conversation">
        <article class="coach-welcome"><b>你好，我是青禾 AI 教练</b><p>可以询问动作要领、同肌群替代动作和训练安排。涉及疼痛、受伤或疾病时不会提供诊断。</p><div><button v-for="item in examples" :key="item" type="button" @click="useExample(item)">{{item}}</button></div></article>
        <template v-for="entry in messages" :key="entry.id">
          <p class="coach-user-message">{{entry.question}}</p>
          <article class="coach-agent-message"><div class="coach-answer-kind"><span>{{entry.response.used_llm?'云端 Agent':'本地检索'}}</span><small>{{entry.response.model_note}}</small></div><p>{{entry.response.answer}}</p><p v-if="entry.response.safety_note" class="coach-safety-note">{{entry.response.safety_note}}</p>
            <div v-if="entry.response.references.length" class="coach-related-actions"><b>相关动作</b><div><span v-for="item in entry.response.references" :key="item.id">{{exerciseNameLabel(item.name)}}</span></div></div>
            <details v-if="entry.response.knowledge_sources.length" class="coach-sources"><summary>查看 {{entry.response.knowledge_sources.length}} 条参考资料</summary><article v-for="source in entry.response.knowledge_sources" :key="source.document_key"><b>{{source.title}}</b><small>{{source.source_name}}<template v-if="source.source_published_at"> · {{source.source_published_at}}</template></small><p>{{source.excerpt}}</p><a v-if="source.source_url" :href="source.source_url" target="_blank" rel="noopener noreferrer">查看来源</a></article></details>
          </article>
        </template>
        <p v-if="error" class="coach-inline-error" role="alert">{{error}}</p>
      </div>
      <form class="coach-composer" @submit.prevent="submit"><label><span class="sr-only">向 AI 教练提问</span><textarea ref="textarea" v-model="question" rows="2" maxlength="500" placeholder="询问动作、替代方案或训练安排…" @keydown.enter.exact.prevent="submit"/></label><div><label class="coach-consent"><input v-model="consent" type="checkbox"><span>允许调用云端模型</span></label><button class="coach-send" type="submit" :disabled="intelligence.asking||!question.trim()"><span>{{intelligence.asking?'检索中':'发送'}}</span><svg viewBox="0 0 20 20"><path d="m4 10 11-6-3 12-2.5-4L4 10Zm5.5 2L15 4"/></svg></button></div><small>未授权时使用本地检索；不会发送账号名。Ctrl + Shift + K 快速打开。</small></form>
    </aside>
  </Teleport>
</template>
