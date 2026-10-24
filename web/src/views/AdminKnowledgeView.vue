<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError } from '@/api/client'
import { getKnowledge, indexKnowledge, knowledgeFileUrl, listKnowledge, uploadKnowledge } from '@/api/knowledge'
import type { KnowledgeDetail, KnowledgeEntry, KnowledgeFilter, KnowledgeSummary } from '@/api/knowledge'
import { useAuthStore } from '@/stores/auth'
import { createLiveSearch } from '@/utils/liveSearch'
import { safeLink, formatDateValue } from '@/utils/adminPresentation'
import { documentSize, knowledgeIndexLabels, knowledgeKindLabels, validateKnowledgeFile } from '@/utils/knowledgeUpload'
import { equipmentLabel, muscleLabel } from '@/utils/exerciseLabels'
import PageHeader from '@/components/ui/PageHeader.vue'
import BaseDialog from '@/components/common/BaseDialog.vue'

const auth = useAuthStore()
const router = useRouter()
const keyword = ref('')
const query = ref('')
const filter = ref<KnowledgeFilter>('all')
const entries = ref<KnowledgeEntry[]>([])
const summary = ref<KnowledgeSummary>({ documents: 0, uploads: 0, segments: 0, active_segments: 0 })
const total = ref(0)
const page = ref(1)
const listBusy = ref(false)
const detailBusy = ref(false)
const detail = ref<KnowledgeDetail | null>(null)
const selected = ref('')
const listError = ref('')
const detailError = ref('')
const feedback = ref('')
const cloudConsent = ref(false)
const indexBusy = ref<number | null>(null)
const indexError = ref('')
const uploadDialog = ref<InstanceType<typeof BaseDialog> | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const searchInput = ref<HTMLInputElement | null>(null)
const file = ref<File | null>(null)
const title = ref('')
const sourceName = ref('')
const sourceUrl = ref('')
const uploadError = ref('')
const uploading = ref(false)
const pages = computed(() => Math.max(1, Math.ceil(total.value / 20)))
const sourceLink = computed(() => safeLink(detail.value?.source_url))
const selectedKey = (entry: Pick<KnowledgeEntry, 'kind' | 'id'>): string => entry.kind + ':' + entry.id
let revision = 0
let resetting = false
let listRequest: AbortController | null = null
let detailRequest: AbortController | null = null
let uploadRequest: AbortController | null = null
let indexRequest: AbortController | null = null

function cancelReads(): void {
  listRequest?.abort(); detailRequest?.abort(); listRequest = null; detailRequest = null
}
function clearReads(): void {
  entries.value = []; total.value = 0; page.value = 1
  selected.value = ''; detail.value = null; cloudConsent.value = false
  listError.value = ''; detailError.value = ''; detailBusy.value = false
}
function resetForm(): void {
  file.value = null; title.value = ''; sourceName.value = ''; sourceUrl.value = ''; uploadError.value = ''
  if (fileInput.value) fileInput.value.value = ''
}
function resetAll(): void {
  cancelReads(); uploadRequest?.abort(); indexRequest?.abort()
  uploadRequest = null; indexRequest = null; clearReads(); resetForm()
  uploading.value = false; indexBusy.value = null; listBusy.value = false
  indexError.value = ''; feedback.value = ''
  summary.value = { documents: 0, uploads: 0, segments: 0, active_segments: 0 }
  uploadDialog.value?.close()
}
function errorMessage(error: unknown): string {
  if (error instanceof ApiError && [401, 403].includes(error.status || 0)) {
    ++revision; searcher.reset(); resetAll()
    void auth.initializeSession(); void router.replace({ name: 'today' })
  }
  return error instanceof Error ? error.message : '操作失败，请稍后重试。'
}
async function loadList(targetPage = 1, preferred = selected.value): Promise<void> {
  cancelReads()
  const controller = new AbortController(); listRequest = controller
  const version = revision
  clearReads(); listBusy.value = true
  try {
    const result = await listKnowledge(query.value, filter.value, targetPage, controller.signal)
    if (controller.signal.aborted || version !== revision || !auth.isAdmin) return
    entries.value = result.items; total.value = result.total; page.value = result.page; summary.value = result.summary
    const chosen = result.items.find(entry => selectedKey(entry) === preferred) || result.items[0]
    if (chosen) void selectDocument(chosen)
  } catch (error) {
    if (!controller.signal.aborted && version === revision) listError.value = errorMessage(error)
  } finally { if (listRequest === controller) listBusy.value = false }
}
async function selectDocument(entry: Pick<KnowledgeEntry, 'kind' | 'id'>): Promise<void> {
  detailRequest?.abort()
  const controller = new AbortController(); detailRequest = controller
  const version = revision
  selected.value = selectedKey(entry); detail.value = null; detailError.value = ''
  indexError.value = ''; cloudConsent.value = false; detailBusy.value = true
  try {
    const result = await getKnowledge(entry.kind, entry.id, controller.signal)
    if (controller.signal.aborted || version !== revision || selected.value !== selectedKey(entry) || !auth.isAdmin) return
    detail.value = result
  } catch (error) {
    if (!controller.signal.aborted && version === revision) detailError.value = errorMessage(error)
  } finally { if (detailRequest === controller) detailBusy.value = false }
}
const searcher = createLiveSearch(
  value => { if (auth.isAdmin) { query.value = value; void loadList(1) } },
  value => { if (auth.isAdmin) { cancelReads(); clearReads(); query.value = value; listBusy.value = true } },
)
watch(keyword, value => { if (!resetting) searcher.update(value) }, { flush: 'sync' })
function endComposition(event: CompositionEvent): void {
  keyword.value = (event.target as HTMLInputElement).value
  searcher.endComposition(keyword.value)
}
function clearSearch(): void { keyword.value = ''; searchInput.value?.focus() }
function openUpload(): void { resetForm(); feedback.value = ''; uploadDialog.value?.open() }
function chooseFile(event: Event): void {
  const previous = file.value?.name
  file.value = (event.target as HTMLInputElement).files?.[0] || null
  uploadError.value = validateKnowledgeFile(file.value) || ''
  if (file.value && !uploadError.value) {
    title.value = file.value.name.replace(/\.[^.]+$/, '').slice(0, 200)
    if (!sourceName.value || sourceName.value === previous) sourceName.value = file.value.name.slice(0, 180)
  }
}
async function submitUpload(): Promise<void> {
  uploadError.value = validateKnowledgeFile(file.value) || ''
  if (uploadError.value || !file.value || uploading.value || !auth.isAdmin) return
  const controller = new AbortController(); uploadRequest = controller
  const version = revision
  uploading.value = true
  try {
    const result = await uploadKnowledge(file.value, { title: title.value, source_name: sourceName.value, source_url: sourceUrl.value }, controller.signal)
    if (controller.signal.aborted || version !== revision || !auth.isAdmin) return
    feedback.value = result.message
    uploadDialog.value?.close(); resetForm()
    searcher.reset(); resetting = true; keyword.value = ''; resetting = false
    query.value = ''; filter.value = 'uploaded'
    await loadList(1, selectedKey(result.document))
  } catch (error) {
    if (!controller.signal.aborted && version === revision) uploadError.value = errorMessage(error)
  } finally { if (uploadRequest === controller) uploading.value = false }
}
async function buildIndex(): Promise<void> {
  if (!detail.value || detail.value.kind !== 'uploaded' || !cloudConsent.value || indexBusy.value !== null || !auth.isAdmin) return
  const id = detail.value.id
  const controller = new AbortController(); indexRequest = controller
  const version = revision
  indexBusy.value = id; indexError.value = ''; feedback.value = ''
  try {
    const result = await indexKnowledge(id, cloudConsent.value, controller.signal)
    if (controller.signal.aborted || version !== revision || !auth.isAdmin) return
    feedback.value = result.message
    entries.value = entries.value.map(entry => entry.kind === 'uploaded' && entry.id === id ? { ...entry, ...result.document } : entry)
    if (detail.value?.kind === 'uploaded' && detail.value.id === id) {
      detail.value = result.document; cloudConsent.value = false
    }
  } catch (error) {
    if (!controller.signal.aborted && version === revision) {
      const message = errorMessage(error)
      if (detail.value?.kind === 'uploaded' && detail.value.id === id) {
        indexError.value = message
        if (error instanceof ApiError && error.status === 502) detail.value.index_status = 'failed'
      }
    }
  } finally { if (indexRequest === controller) indexBusy.value = null }
}
watch(() => [auth.user?.id, auth.isAdmin] as const, () => {
  ++revision; searcher.reset(); resetAll()
  resetting = true; keyword.value = ''; resetting = false; query.value = ''; filter.value = 'all'
  if (auth.isAdmin) void loadList()
  else if (router.currentRoute.value.name === 'admin-knowledge') void router.replace({ name: 'today' })
}, { immediate: true, flush: 'sync' })
onBeforeUnmount(() => { ++revision; searcher.dispose(); resetAll() })
</script>

<template>
  <section v-if="auth.isAdmin" class="page active knowledge-page">
    <PageHeader title="RAG 知识库" description="管理 AI 教练回答时使用的训练资料">
      <template #actions><button class="knowledge-primary" type="button" @click="openUpload">上传文档</button></template>
    </PageHeader>
    <div class="knowledge-stats" aria-label="知识库概况">
      <article><span>文档总数</span><b>{{ summary.documents }}</b></article>
      <article><span>上传文档</span><b>{{ summary.uploads }}</b></article>
      <article><span>检索分段</span><b>{{ summary.segments }}</b></article>
      <article><span>可用分段</span><b>{{ summary.active_segments }}</b></article>
    </div>
    <p v-if="feedback" class="knowledge-feedback" role="status">{{ feedback }}</p>
    <div class="knowledge-layout">
      <aside class="knowledge-directory" aria-label="知识文档目录">
        <form class="admin-search" @submit.prevent="searcher.flush(keyword)">
          <label for="knowledge-search">文档标题或来源<input id="knowledge-search" ref="searchInput" v-model="keyword" maxlength="200" autocomplete="off" placeholder="输入后自动搜索" @compositionstart="searcher.startComposition" @compositionend="endComposition" /></label>
          <button type="button" :disabled="!keyword" @click="clearSearch">清空</button>
        </form>
        <label class="knowledge-filter">资料类型<select v-model="filter" @change="searcher.flush(keyword)">
          <option value="all">全部文档</option><option value="exercise">动作资料</option>
          <option value="external">公开资料</option><option value="uploaded">上传文档</option>
        </select></label>
        <p class="knowledge-result-count" role="status">{{ listBusy ? '正在加载文档…' : total + ' 份文档' }}</p>
        <p v-if="listError" class="admin-error" role="alert">{{ listError }} <button @click="loadList(page)">重试</button></p>
        <p v-else-if="!listBusy && !entries.length" class="admin-empty">暂无匹配文档，可以调整关键词或上传新资料。</p>
        <ul v-else class="knowledge-documents">
          <li v-for="entry in entries" :key="selectedKey(entry)">
            <button type="button" :class="{ selected: selected === selectedKey(entry) }" :aria-pressed="selected === selectedKey(entry)" @click="selectDocument(entry)">
              <span class="knowledge-kind">{{ knowledgeKindLabels[entry.kind] }}</span><strong>{{ entry.title }}</strong>
              <span>{{ entry.source_name }}</span><small>{{ entry.characters.toLocaleString() }} 字 · {{ entry.chunk_count }} 段</small>
            </button>
          </li>
        </ul>
        <nav v-if="total > 20" class="admin-pagination" aria-label="文档分页">
          <button :disabled="listBusy || page <= 1" @click="loadList(page - 1)">上一页</button>
          <span>{{ page }} / {{ pages }}</span><button :disabled="listBusy || page >= pages" @click="loadList(page + 1)">下一页</button>
        </nav>
      </aside>
      <section class="knowledge-detail" aria-label="文档详情" :aria-busy="detailBusy">
        <p v-if="detailError" class="admin-error" role="alert">{{ detailError }} <button @click="loadList(page)">重新加载</button></p>
        <p v-else-if="detailBusy" class="admin-empty" role="status">正在读取文档…</p>
        <template v-else-if="detail">
          <header class="knowledge-document-head">
            <div><span class="knowledge-kind">{{ knowledgeKindLabels[detail.kind] }}</span><h3>{{ detail.title }}</h3><p>{{ detail.source_name }}</p></div>
            <a v-if="detail.kind === 'uploaded'" :href="knowledgeFileUrl(detail.id)" class="knowledge-download">下载原文</a>
          </header>
          <dl class="knowledge-meta">
            <div><dt>录入 / 更新时间</dt><dd>{{ formatDateValue(detail.created_at) }}</dd></div>
            <div><dt>文字与分段</dt><dd>{{ detail.characters.toLocaleString() }} 字 · {{ detail.chunk_count }} 段</dd></div>
            <div><dt>教练检索</dt><dd>{{ detail.review_status === 'approved' ? '已启用本地检索' : '尚未启用' }}</dd></div>
            <div v-if="detail.file_size"><dt>原文件</dt><dd>{{ detail.file_type?.toUpperCase() }} · {{ documentSize(detail.file_size) }}</dd></div>
            <div v-if="sourceLink"><dt>资料链接</dt><dd><a :href="sourceLink" target="_blank" rel="noopener noreferrer">查看原始来源 ↗</a></dd></div>
            <div v-if="detail.source_published_at"><dt>来源发布日期</dt><dd>{{ detail.source_published_at }}</dd></div>
            <div v-if="detail.target_muscles?.length"><dt>目标肌群</dt><dd>{{ detail.target_muscles.map(muscleLabel).join('、') }}</dd></div>
            <div v-if="detail.equipment?.length"><dt>适用器械</dt><dd>{{ detail.equipment.map(equipmentLabel).join('、') }}</dd></div>
          </dl>
          <section v-if="detail.kind === 'uploaded'" class="knowledge-index-panel">
            <h4>{{ knowledgeIndexLabels[detail.index_status] || '语义索引状态待确认' }}</h4>
            <p>文档已可用于本地检索。生成语义索引后，可结合向量检索查找语义相近的内容。</p>
            <p v-if="detail.indexed_at">上次生成：{{ formatDateValue(detail.indexed_at) }}</p>
            <label class="knowledge-consent"><input v-model="cloudConsent" type="checkbox" :disabled="indexBusy !== null || detail.index_status === 'indexing'" /><span>允许将本文档文字发送到已配置的云端模型，生成语义索引。</span></label>
            <div class="knowledge-index-actions">
              <button type="button" :disabled="!cloudConsent || indexBusy !== null || detail.index_status === 'indexing'" @click="buildIndex">{{ indexBusy === detail.id ? '正在生成语义索引…' : detail.index_status === 'indexed' ? '重新生成语义索引' : '生成语义索引' }}</button>
              <button type="button" :disabled="indexBusy !== null" @click="selectDocument(detail)">刷新状态</button>
            </div>
            <p v-if="indexError" class="knowledge-error" role="alert">{{ indexError }}</p>
            <p v-else-if="detail.index_error" class="knowledge-error">{{ detail.index_error }}</p>
          </section>
          <h4 class="knowledge-body-title">文档内容</h4>
          <div class="knowledge-body" tabindex="0" aria-label="文档正文">{{ detail.body }}</div>
        </template>
        <p v-else class="admin-empty">从左侧选择文档，查看资料内容与来源。</p>
      </section>
    </div>
    <BaseDialog ref="uploadDialog" class="knowledge-upload-dialog" aria-labelledby="knowledge-upload-title" :dismissible="!uploading">
      <header><h3 id="knowledge-upload-title">上传知识文档</h3><button type="button" aria-label="关闭上传窗口" :disabled="uploading" @click="uploadDialog?.close()">×</button></header>
      <p>上传的资料会加入共享知识库，用于所有用户的 AI 教练回答。</p>
      <form @submit.prevent="submitUpload">
        <fieldset :disabled="uploading">
          <label>选择文件<input ref="fileInput" type="file" accept=".txt,.md,.pdf,.docx" required aria-describedby="knowledge-file-help" @change="chooseFile" /></label>
          <small id="knowledge-file-help">支持 TXT、Markdown、PDF、DOCX，单个文件不超过10 MB。扫描版 PDF 请先识别文字。</small>
          <p v-if="file" class="knowledge-file-selected">{{ file.name }} · {{ documentSize(file.size) }}</p>
          <label>文档标题<input v-model="title" maxlength="200" placeholder="默认使用文件名" /></label>
          <label>资料来源<input v-model="sourceName" maxlength="180" placeholder="例如：训练指南、专业机构或作者" /></label>
          <label>原文链接（选填）<input v-model="sourceUrl" type="url" maxlength="2000" placeholder="https://" /></label>
        </fieldset>
        <p v-if="uploadError" class="knowledge-error" role="alert">{{ uploadError }}</p>
        <p class="knowledge-upload-note">上传后自动提取文字并分段，可立即用于本地检索。语义索引需在文档详情中另行确认生成。</p>
        <footer><button type="button" :disabled="uploading" @click="uploadDialog?.close()">取消</button><button class="knowledge-primary" type="submit" :disabled="uploading || !file">{{ uploading ? '正在解析并保存…' : '上传并加入知识库' }}</button></footer>
      </form>
    </BaseDialog>
  </section>
</template>
