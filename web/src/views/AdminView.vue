<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ApiError } from '@/api/client'
import { adminPhotoUrl, getAdminRecords, getAdminUser, listAdminUsers } from '@/api/admin'
import type { AdminUser, RecordPage, UserDetail } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/ui/PageHeader.vue'
import AdminDataValue from '@/components/admin/AdminDataValue.vue'
import { itemHeading } from '@/utils/adminPresentation'
import { createLiveSearch } from '@/utils/liveSearch'

const auth = useAuthStore()
const router = useRouter()
const keyword = ref('')
const searchInput = ref<HTMLInputElement | null>(null)
let resettingSearch = false
const query = ref('')
const users = ref<AdminUser[]>([])
const total = ref(0)
const listPage = ref(1)
const selectedId = ref<number | null>(null)
const detail = ref<UserDetail | null>(null)
const dataset = ref('')
const records = ref<RecordPage | null>(null)
const listBusy = ref(false)
const detailBusy = ref(false)
const recordBusy = ref(false)
const listError = ref('')
const detailError = ref('')
const recordError = ref('')
let listRequest: AbortController | null = null
let detailRequest: AbortController | null = null
let recordRequest: AbortController | null = null
let epoch = 0
const listPages = computed(() => Math.max(1, Math.ceil(total.value / 20)))
const recordPages = computed(() => Math.max(1, Math.ceil((records.value?.total || 0) / 20)))
const selectedDataset = computed(() => detail.value?.datasets.find(item => item.key === dataset.value))

function cancelRequests(): void {
  listRequest?.abort(); detailRequest?.abort(); recordRequest?.abort()
  listRequest = null; detailRequest = null; recordRequest = null
}
function clearData(): void {
  users.value = []; total.value = 0; detail.value = null; records.value = null
  selectedId.value = null; dataset.value = ''; listPage.value = 1
  listError.value = ''; detailError.value = ''; recordError.value = ''
  listBusy.value = false; detailBusy.value = false; recordBusy.value = false
}
function fail(error: unknown): string {
  if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
    searcher.reset(); ++epoch; cancelRequests(); clearData()
    void auth.initializeSession(); void router.replace({ name: 'today' })
  }
  return error instanceof Error ? error.message : '加载失败，请重试。'
}
async function loadUsers(page = 1): Promise<void> {
  listRequest?.abort()
  const controller = new AbortController(); listRequest = controller
  const version = epoch
  listBusy.value = true; listError.value = ''
  detailRequest?.abort(); recordRequest?.abort()
  users.value = []; detail.value = null; records.value = null; selectedId.value = null
  try {
    const result = await listAdminUsers(query.value, page, controller.signal)
    if (controller.signal.aborted || version !== epoch || !auth.isAdmin) return
    users.value = result.items; total.value = result.total; listPage.value = result.page
    const first = result.items[0]
    if (first) void selectUser(first.id)
  } catch (error) {
    if (!controller.signal.aborted && version === epoch) listError.value = fail(error)
  } finally { if (listRequest === controller) listBusy.value = false }
}
const searcher = createLiveSearch(
  (value) => {
    if (!auth.isAdmin) return
    query.value = value
    void loadUsers(1)
  },
  (value) => {
    if (!auth.isAdmin) return
    ++epoch; cancelRequests(); clearData()
    query.value = value; listBusy.value = true
  },
)
watch(keyword, (value) => { if (!resettingSearch) searcher.update(value) }, { flush: 'sync' })
function search(): void { searcher.flush(keyword.value) }
function clearSearch(): void { keyword.value = ''; searchInput.value?.focus() }
function finishComposition(event: CompositionEvent): void {
  const value = (event.target as HTMLInputElement).value
  keyword.value = value
  searcher.endComposition(value)
}
async function selectUser(id: number): Promise<void> {
  detailRequest?.abort(); recordRequest?.abort()
  const controller = new AbortController(); detailRequest = controller
  const version = epoch
  selectedId.value = id; detail.value = null; records.value = null; dataset.value = ''
  detailError.value = ''; recordError.value = ''; detailBusy.value = true
  try {
    const result = await getAdminUser(id, controller.signal)
    if (controller.signal.aborted || version !== epoch || selectedId.value !== id || !auth.isAdmin) return
    detail.value = result
    const first = result.datasets.find(item => item.key === 'body_profiles' && item.count) ||
      result.datasets.find(item => item.count) || result.datasets[0]
    if (first) void loadRecords(first.key)
  } catch (error) {
    if (!controller.signal.aborted && version === epoch) detailError.value = fail(error)
  } finally { if (detailRequest === controller) detailBusy.value = false }
}
async function loadRecords(key = dataset.value, page = 1): Promise<void> {
  if (selectedId.value === null || !key) return
  recordRequest?.abort()
  const controller = new AbortController(); recordRequest = controller
  const version = epoch; const id = selectedId.value
  dataset.value = key; records.value = null; recordBusy.value = true; recordError.value = ''
  try {
    const result = await getAdminRecords(id, key, page, controller.signal)
    if (controller.signal.aborted || version !== epoch || selectedId.value !== id || !auth.isAdmin) return
    records.value = result
  } catch (error) {
    if (!controller.signal.aborted && version === epoch) recordError.value = fail(error)
  } finally { if (recordRequest === controller) recordBusy.value = false }
}
function changeDataset(event: Event): void { void loadRecords((event.target as HTMLSelectElement).value) }
function formatDate(value: string): string {
  const day = new Date(value)
  return Number.isNaN(day.getTime()) ? value : day.toLocaleString('zh-CN', { hour12: false })
}
watch(() => [auth.user?.id, auth.isAdmin] as const, () => {
  searcher.reset(); ++epoch; cancelRequests(); clearData()
  resettingSearch = true; keyword.value = ''; query.value = ''; resettingSearch = false
  if (auth.isAdmin) void loadUsers()
  else if (router.currentRoute.value.name === 'admin') void router.replace({ name: 'today' })
}, { immediate: true, flush: 'sync' })
onBeforeUnmount(() => { searcher.dispose(); ++epoch; cancelRequests(); clearData() })
</script>

<template>
  <section v-if="auth.isAdmin" class="page active admin-page">
    <PageHeader title="用户管理" description="查看用户档案与业务记录">
      <template #actions><span class="admin-role">管理员 · 只读查看</span></template>
    </PageHeader>
    <div class="admin-workspace">
      <aside class="admin-directory" aria-label="用户目录">
        <div class="admin-directory-head"><h3>用户目录</h3><span role="status" aria-live="polite">{{ listBusy ? '搜索中…' : total + ' 位' + (query ? '匹配用户' : '用户') }}</span></div>
        <form class="admin-search" @submit.prevent="search">
          <label for="admin-search">用户名或昵称<input id="admin-search" ref="searchInput" v-model="keyword" maxlength="100" autocomplete="off" placeholder="输入用户名或昵称" aria-describedby="admin-search-hint" @compositionstart="searcher.startComposition" @compositionend="finishComposition" /></label>
          <button type="button" :disabled="!keyword" aria-label="清空搜索并显示全部用户" @click="clearSearch">清空</button>
        </form>
        <p id="admin-search-hint" class="admin-search-hint">输入后自动搜索</p>
        <p v-if="listError" class="admin-error" role="alert">{{ listError }} <button type="button" @click="loadUsers(listPage)">重试</button></p>
        <p v-else-if="listBusy" class="admin-empty" role="status">正在搜索用户…</p>
        <p v-else-if="!users.length" class="admin-empty">没有找到用户，请尝试其他关键词。</p>
        <ul v-else class="admin-users">
          <li v-for="user in users" :key="user.id">
            <button type="button" :class="{ selected: selectedId === user.id }" :aria-pressed="selectedId === user.id" @click="selectUser(user.id)">
              <span class="admin-avatar" aria-hidden="true">{{ (user.display_name || user.username).slice(0, 1) }}</span>
              <span class="admin-user-name"><b>{{ user.display_name }}</b><small>{{ user.username }}</small></span>
              <span class="admin-user-role">{{ user.is_admin ? '管理员' : '用户' }}</span>
            </button>
          </li>
        </ul>
        <nav v-if="total > 20" class="admin-pagination" aria-label="用户目录分页">
          <button :disabled="listBusy || listPage <= 1" @click="loadUsers(listPage - 1)">上一页</button>
          <span>{{ listPage }} / {{ listPages }}</span>
          <button :disabled="listBusy || listPage >= listPages" @click="loadUsers(listPage + 1)">下一页</button>
        </nav>
      </aside>
      <section class="admin-detail" aria-label="用户详情" :aria-busy="detailBusy || recordBusy">
        <p v-if="detailError" class="admin-error" role="alert">{{ detailError }} <button v-if="selectedId" @click="selectUser(selectedId)">重试</button></p>
        <p v-else-if="detailBusy" class="admin-empty" role="status">正在加载用户资料…</p>
        <template v-else-if="detail">
          <header class="admin-detail-head">
            <div><p class="admin-eyebrow">用户 #{{ detail.user.id }}</p><h3>{{ detail.user.display_name }}</h3><p>{{ detail.user.username }} · {{ detail.user.is_admin ? '管理员' : '普通用户' }}</p></div>
            <span>注册于 {{ formatDate(detail.user.created_at) }}</span>
          </header>
          <label class="admin-dataset-select">查看数据类别
            <select :value="dataset" @change="changeDataset">
              <option v-for="item in detail.datasets" :key="item.key" :value="item.key">{{ item.label }}（{{ item.count }}）</option>
            </select>
          </label>
          <div class="admin-record-heading"><h4>{{ selectedDataset?.label }}</h4><span>{{ records?.total ?? selectedDataset?.count ?? 0 }} 条记录</span></div>
          <p v-if="recordError" class="admin-error" role="alert">{{ recordError }} <button @click="loadRecords()">重试</button></p>
          <p v-else-if="recordBusy" class="admin-empty" role="status">正在读取记录…</p>
          <p v-else-if="!records?.items.length" class="admin-empty">该用户还没有这类记录。</p>
          <template v-else>
            <article v-for="(row, index) in records.items" :key="String(row.id ?? index)" class="admin-record">
              <header><b>{{ itemHeading(row, (records.page - 1) * records.page_size + index, selectedDataset?.label || "记录", dataset) }}</b>
                <a v-if="dataset === 'shape_photos' && typeof row.id === 'number'" :href="adminPhotoUrl(detail.user.id, row.id)" target="_blank" rel="noopener noreferrer">查看照片 ↗</a>
              </header>
              <AdminDataValue :value="row" field="record" :dataset="dataset" :exercise-names="records.exercise_names || {}" :omit-fields="['id']" />
            </article>
            <nav v-if="records.total > records.page_size" class="admin-pagination" aria-label="业务记录分页">
              <button :disabled="recordBusy || records.page <= 1" @click="loadRecords(dataset, records.page - 1)">上一页</button>
              <span>{{ records.page }} / {{ recordPages }}</span>
              <button :disabled="recordBusy || records.page >= recordPages" @click="loadRecords(dataset, records.page + 1)">下一页</button>
            </nav>
          </template>
        </template>
        <p v-else-if="!listBusy" class="admin-empty">从用户目录选择一位用户，查看其资料与记录。</p>
      </section>
    </div>
  </section>
</template>
