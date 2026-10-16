// 浏览器端交互入口：请求 FastAPI、更新页面，并跟踪安全筛查和计划浏览状态。
const $ = (selector) => document.querySelector(selector)
const $$ = (selector) => [...document.querySelectorAll(selector)]
// safetyStatus 表示服务端筛查状态；其余变量只缓存当前浏览器已加载的历史列表和选择项。

let safetyStatus = 'loading'
let screeningDate = null
let planHistory = []
let historyCursor = null
let historyCurrentWeekStart = null
let selectedPlanWeek = null
let historyLoading = false
let planPreferencesLoaded = false
let planPreferencesLoading = false
let planFormEdited = false

const EXPERIENCE_LABELS = {
  beginner: "刚开始训练",
  some_experience: "有一些经验",
  experienced: "经验较丰富",
}
const EQUIPMENT_LABELS = {
  bodyweight_only: "仅自重",
  dumbbells: "哑铃",
  resistance_bands: "弹力带",
  gym: "健身房常见器械",
}
const WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


// 统一封装 fetch，把服务端错误转换为带 HTTP 状态码的异常，供安全门禁处理。
async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    const message = typeof body.detail === 'string' ? body.detail : '请求失败，请稍后重试。'
    const error = new Error(message)
    error.status = response.status
    throw error
  }
  return body
}

let noticeReturnFocus = null

// 全站提示统一放入居中对话框；打开时把焦点移入弹窗，关闭后交还给触发位置。
function notify(message, kind = 'info') {
  const modal = $('#notice-modal')
  const wasHidden = modal.classList.contains('hidden')
  if (wasHidden) noticeReturnFocus = document.activeElement
  modal.querySelector('.alert-modal').dataset.kind = kind
  $('#notice-modal-title').textContent = kind === 'error' ? '请检查一下' : '提示'
  $('#notice-modal-icon').textContent = kind === 'error' ? '!' : 'i'
  $('#notice-modal-message').textContent = message
  modal.classList.remove('hidden')
  $('#notice-modal-close').focus()
}

function closeNoticeModal() {
  const modal = $('#notice-modal')
  if (modal.classList.contains('hidden')) return
  modal.classList.add('hidden')
  noticeReturnFocus?.focus()
  noticeReturnFocus = null
}

$('#notice-modal-close').addEventListener('click', closeNoticeModal)
document.addEventListener('keydown', (event) => {
  if ($('#notice-modal').classList.contains('hidden')) return
  if (event.key === 'Escape') {
    closeNoticeModal()
  } else if (event.key === 'Tab') {
    event.preventDefault()
    $('#notice-modal-close').focus()
  }
})

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char])
}

// 页面切换不重新载入文档；进入页面时按需向后端刷新对应数据。
function showPage(name) {
  // 先立即更新导航和页面，避免后续安全状态刷新影响用户的切页反馈。
$$('.tab').forEach((tab) => tab.classList.toggle('active', tab.dataset.page === name))
$$('.page').forEach((page) => page.classList.toggle('active', page.id === `page-${name}`))
  expireScreeningForNewDay()
  if (name === 'today') refreshToday()
  if (name === 'plan') {
    if (safetyStatus === 'clear') {
      loadPlanPreferences()
      refreshCurrentPlan()
    } else hidePlanForSafety('请先完成安全筛查，再查看本周计划。')
  }
  if (name === 'profile') loadBodyProfile()
  if (name === 'log') refreshLogs()
  if (name === 'review') refreshWeeklyReview()
}

// 身体档案保存在后端数据库；浏览器只记住用户是否跳过首次建档提示。
const AGE_BAND_LABELS = { under_18: '未满 18 岁', '18_29': '18–29 岁', '30_44': '30–44 岁', '45_59': '45–59 岁', '60_plus': '60 岁及以上' }
let profileExists = false
let activeAccount = null
let applicationStarted = false
let profileOnboarding = false
let profileModalReturnFocus = null

function wasProfilePromptSkipped() {
  try { return localStorage.getItem('fitnessCoachProfilePromptSkipped:' + activeAccount.id) === 'true' } catch { return false }
}
function rememberProfilePromptSkipped() {
  try { localStorage.setItem('fitnessCoachProfilePromptSkipped:' + activeAccount.id, 'true') } catch { /* 浏览器禁用存储时仍可继续使用 */ }
}
function openBodyProfileModal({ onboarding = false } = {}) {
  profileOnboarding = onboarding
  profileModalReturnFocus = document.activeElement
  $('#body-profile-modal').classList.remove('hidden')
  $('#close-body-profile-modal').classList.toggle('hidden', onboarding)
  $('#skip-body-profile').classList.toggle('hidden', !onboarding)
  $('#body-profile-modal-title').textContent = onboarding ? '先认识一下你的训练起点' : (profileExists ? '编辑个人身体档案' : '填写个人身体档案')
  $('#body-profile-modal-description').textContent = '填写身体基础数据，后续计划可以参考这些信息。带“选填”的项目可以留空；你也可以跳过，之后在“我的”页面继续填写。'
  $('#body-profile-form').elements.age_band.focus()
}
function closeBodyProfileModal({ skipped = false } = {}) {
  $('#body-profile-modal').classList.add('hidden')
  if (skipped) rememberProfilePromptSkipped()
  profileModalReturnFocus?.focus()
  profileModalReturnFocus = null
  profileOnboarding = false
}

// 进入“我的”时从服务器加载档案；首次无档案且未跳过时打开可略过的建档弹窗。
async function loadBodyProfile({ promptIfNeeded = false } = {}) {
  const form = $('#body-profile-form')
  const editButton = $('#edit-body-profile')
  const removeButton = $('#delete-body-profile')
  const summary = $('#body-profile-summary')
  const historyContainer = $('#body-weight-history')
  try {
    const result = await api('/api/body-profile')
    const profile = result.profile
    profileExists = Boolean(profile)
    if (!profile) {
      form.reset()
      editButton.textContent = '填写身体档案'
      removeButton.classList.add('hidden')
      summary.className = 'empty-state profile-empty'
      summary.innerHTML = '<span class="profile-empty-icon" aria-hidden="true">＋</span><h4>还没有身体档案</h4><p>填写年龄段、身高和体重，后续生成计划时会参考这些基础数据。</p>'
      historyContainer.className = 'empty-state profile-empty'
      historyContainer.innerHTML = '<p>保存首次身体档案后，这里会开始记录体重变化。</p>'
      if (promptIfNeeded && !wasProfilePromptSkipped()) openBodyProfileModal({ onboarding: true })
      return
    }
    form.elements.age_band.value = profile.age_band
    form.elements.height_cm.value = profile.height_cm
    form.elements.weight_kg.value = profile.weight_kg
    form.elements.body_fat_percent.value = profile.body_fat_percent ?? ''
    form.elements.waist_cm.value = profile.waist_cm ?? ''
    editButton.textContent = '编辑身体档案'
    removeButton.classList.remove('hidden')
    const optional = [
      profile.body_fat_percent == null ? '' : `体脂率 ${escapeHtml(profile.body_fat_percent)}%`,
      profile.waist_cm == null ? '' : `腰围 ${escapeHtml(profile.waist_cm)} 厘米`,
    ].filter(Boolean)
    summary.className = 'profile-summary'
    summary.innerHTML = `<div class="profile-metrics"><div><span>年龄段</span><b>${escapeHtml(AGE_BAND_LABELS[profile.age_band] || '未记录')}</b></div><div><span>身高</span><b>${escapeHtml(profile.height_cm)} <small>cm</small></b></div><div><span>当前体重</span><b>${escapeHtml(profile.weight_kg)} <small>kg</small></b></div></div>${optional.length ? `<p class="profile-optional">${optional.map(escapeHtml).join('　·　')}</p>` : ''}<p class="profile-updated">档案更新于 ${escapeHtml(profile.updated_at)}</p>`
    const history = (result.weight_history || []).slice(0, 8)
    historyContainer.className = history.length ? 'weight-history-list' : 'empty-state profile-empty'
    historyContainer.innerHTML = history.length
      ? `<ul>${history.map((item) => `<li><time>${escapeHtml(item.date)}</time><b>${escapeHtml(item.weight_kg)} <small>kg</small></b></li>`).join('')}</ul>`
      : '<p>暂无体重历史。</p>'
  } catch (error) {
    notify(error.message, 'error')
  }
}

$('#edit-body-profile').addEventListener('click', () => openBodyProfileModal())
$('#close-body-profile-modal').addEventListener('click', () => closeBodyProfileModal())
$('#skip-body-profile').addEventListener('click', () => closeBodyProfileModal({ skipped: true }))
$('#body-profile-modal').addEventListener('click', (event) => {
  if (event.target.id !== 'body-profile-modal') return
  if (profileOnboarding) closeBodyProfileModal({ skipped: true })
  else closeBodyProfileModal()
})
document.addEventListener('keydown', (event) => {
  const modal = $('#body-profile-modal')
  if (modal.classList.contains('hidden')) return
  if (event.key === 'Escape') {
    closeBodyProfileModal({ skipped: profileOnboarding })
  } else if (event.key === 'Tab') {
    const focusable = [...modal.querySelectorAll('button:not(.hidden), input, select')].filter((item) => !item.disabled)
    if (!focusable.length) return
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
  }
})

$('#body-profile-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const form = event.currentTarget
  const data = new FormData(form)
  const optionalNumber = (name) => data.get(name) ? Number(data.get(name)) : null
  const payload = {
    age_band: data.get('age_band'),
    height_cm: Number(data.get('height_cm')),
    weight_kg: Number(data.get('weight_kg')),
    body_fat_percent: optionalNumber('body_fat_percent'),
    waist_cm: optionalNumber('waist_cm'),
  }
  try {
    const result = await api('/api/body-profile', { method: 'PUT', body: JSON.stringify(payload) })
    closeBodyProfileModal({ skipped: true })
    await loadBodyProfile()
    notify(`${result.message}如要让新档案用于本周安排，请重新生成本周计划。`)
  } catch (error) {
    notify(error.message, 'error')
  }
})

let resolveBodyProfileDelete = null
function confirmBodyProfileDelete() {
  $('#body-profile-delete-modal').classList.remove('hidden')
  $('#cancel-body-profile-delete').focus()
  return new Promise((resolve) => { resolveBodyProfileDelete = resolve })
}
function closeBodyProfileDelete(confirmed) {
  $('#body-profile-delete-modal').classList.add('hidden')
  resolveBodyProfileDelete?.(confirmed)
  resolveBodyProfileDelete = null
}
$('#cancel-body-profile-delete').addEventListener('click', () => closeBodyProfileDelete(false))
$('#confirm-body-profile-delete').addEventListener('click', () => closeBodyProfileDelete(true))
$('#body-profile-delete-modal').addEventListener('click', (event) => {
  if (event.target.id === 'body-profile-delete-modal') closeBodyProfileDelete(false)
})
document.addEventListener('keydown', (event) => {
  const modal = $('#body-profile-delete-modal')
  if (modal.classList.contains('hidden')) return
  if (event.key === 'Escape') closeBodyProfileDelete(false)
  if (event.key === 'Tab') {
    event.preventDefault()
    const active = document.activeElement.id
    $(active === 'cancel-body-profile-delete' ? '#confirm-body-profile-delete' : '#cancel-body-profile-delete').focus()
  }
})
$('#delete-body-profile').addEventListener('click', async () => {
  if (!await confirmBodyProfileDelete()) return
  try {
    const result = await api('/api/body-profile', { method: 'DELETE' })
    notify(result.message)
    await loadBodyProfile()
  } catch (error) {
    notify(error.message, 'error')
  }
})
$$('.tab').forEach((tab) => tab.addEventListener('click', () => showPage(tab.dataset.page)))
$$('[data-goto]').forEach((button) => button.addEventListener('click', () => showPage(button.dataset.goto)))

function planSetupLabel(plan) {
  if (!plan.experience_level || !Array.isArray(plan.equipment) || !plan.session_minutes) return ""
  const experience = EXPERIENCE_LABELS[plan.experience_level] || "训练经验未记录"
  const equipment = plan.equipment.map((item) => EQUIPMENT_LABELS[item] || item).join("、")
  return `${experience} · ${equipment} · 约 ${plan.session_minutes} 分钟/次`
}

function selectedTrainingWeekdays() {
  return $$('input[name="training_weekdays"]:checked')
    .map((input) => Number(input.value))
    .sort((a, b) => a - b)
}

function updateWeekdayCount() {
  const count = selectedTrainingWeekdays().length
  $('#weekday-count').textContent = count === 1 ? '已选 1 天' : `已选 ${count} 天`
}

// 偏好读取受安全门禁保护；只在首次进入计划页时回填，避免覆盖用户正在编辑的值。
async function loadPlanPreferences() {
  if (planPreferencesLoaded || planPreferencesLoading || safetyStatus !== "clear") return
  planPreferencesLoading = true
  try {
    const result = await api("/api/plan/preferences")
    if (safetyStatus !== "clear") return
    if (!planFormEdited) {
      const form = $("#plan-form")
      const preferences = result.preferences
      form.elements.goal.value = preferences.goal
      form.elements.experience_level.value = preferences.experience_level
      form.elements.session_minutes.value = String(preferences.session_minutes)
      $$('input[name="equipment"]').forEach((input) => {
        input.checked = preferences.equipment.includes(input.value)
      })
      $$('input[name="training_weekdays"]').forEach((input) => {
        input.checked = preferences.training_weekdays.includes(Number(input.value))
      })
      updateWeekdayCount()
    }
    planPreferencesLoaded = true
  } catch (error) {
    if (await handleSafetyGateError(error)) return
    notify(error.message, "error")
  } finally {
    planPreferencesLoading = false
  }
}

function levelLabel(level) {
  return ({
    ask: ['等待筛查', '安全筛查尚未完成'],
    stop: ['暂停训练', '已触发安全暂停'],
    insufficient_data: ['信息不足', '缺少今天的主观状态'],
    normal: ['按计划', '依据你主动提供的信息'],
    rest_day: ['计划休息日', '今天无需记录状态'],
    downgrade: ['考虑降负荷', '依据你主动提供的信息'],
  })[level] || ['状态未知', '']
}

// 今日安排卡片只渲染服务端按日期筛选后的单日结果。
function renderTodaySchedule(schedule) {
  if (!schedule) return ""
  const weekday = WEEKDAY_LABELS[Number(schedule.weekday) - 1] || "今天"
  if (schedule.status === "training" && schedule.session) {
    const session = schedule.session
    const duration = session.duration_minutes ? ` · 约 ${escapeHtml(session.duration_minutes)} 分钟` : ""
    return `<div class="today-schedule training-day"><span class="today-schedule-label">今日训练 · ${weekday}</span><b>${escapeHtml(session.title)}${duration}</b><p>${escapeHtml(session.description)}</p></div>`
  }
  if (schedule.status === "rest") {
    return `<div class="today-schedule rest-day"><span class="today-schedule-label">${weekday} · 计划安排</span><b>今天是计划休息日</b><p>这是当前周计划中的安排。</p></div>`
  }
  const isLegacy = schedule.status === "legacy_plan"
  const title = isLegacy ? "本周计划尚无具体星期安排" : "本周还没有保存的计划"
  const message = isLegacy
    ? "旧计划没有记录训练星期，无法准确定位今天的会话。"
    : "可以前往周计划页，选择训练星期并生成计划。"
  return `<div class="today-schedule no-plan"><b>${title}</b><p>${message}</p><button class="text-button" type="button" data-goto="plan">前往周计划 →</button></div>`
}
function showDailySignalForm() {
  $("#signal-form").hidden = false
  $("#rest-day-signal-note").classList.add("hidden")
  $("#signal-panel-title").textContent = "记录今天的状态"
}

// 前端据今日接口同步安全状态；计划接口仍会在服务端再次执行安全门禁。
async function refreshToday() {
  const card = $('#today-card')
  try {
    const result = await api('/api/today')
    const [label, detail] = levelLabel(result.level)
    card.className = `status-card status-${result.level}`
    const isRestDay = result.level === "rest_day"
    if (isRestDay) {
      $("#signal-form").hidden = true
      $("#rest-day-signal-note").classList.remove("hidden")
      $("#signal-panel-title").textContent = "今天是计划休息日"
    } else {
      showDailySignalForm()
    }
    const scheduleMarkup = result.level === "normal" || isRestDay ? renderTodaySchedule(result.today_schedule) : ""
    card.innerHTML = `<div class="status-top"><span class="status-pill"><i></i>${escapeHtml(label)}</span><span class="status-detail">${escapeHtml(detail)}</span></div><h3>${escapeHtml(result.message)}</h3><ul class="reason-list">${(result.reasons || []).map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}</ul>${scheduleMarkup}`
    card.querySelector('[data-goto="plan"]')?.addEventListener("click", () => showPage("plan"))
    if (result.level === 'stop') {
      safetyStatus = 'stop'
      screeningDate = null
      updateSafetyUi()
      hidePlanForSafety(result.message)
    } else if (result.level === 'ask') {
      safetyStatus = 'ask'
      screeningDate = null
      updateSafetyUi()
      hidePlanForSafety(result.message)
    } else {
      safetyStatus = 'clear'
      screeningDate = result.screening_date || localDateString()
      updateSafetyUi()
      await refreshCurrentPlan()
    }
  } catch (error) {
    safetyStatus = 'ask'
    screeningDate = null
    updateSafetyUi()
    card.className = 'status-card status-ask'
    card.textContent = error.message
    hidePlanForUnavailable(error.message)
  }
}
$('#refresh-today').addEventListener('click', refreshToday)

// 用户输入的每日状态仅在安全筛查通过后提交，数据库错误时清空计划展示。
$('#signal-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const data = new FormData(event.currentTarget)
  const readiness = data.get('readiness')
  if (!readiness) return notify('请选择今天的主观状态。', 'error')
  const payload = { readiness }
  if (data.get('sleep_hours') !== '') payload.sleep_hours = Number(data.get('sleep_hours'))
  if (data.get('resting_hr') !== '') payload.resting_hr = Number(data.get('resting_hr'))
  try {
    await api('/api/daily-signal', { method: 'POST', body: JSON.stringify(payload) })
    notify('状态已保存。')
    await refreshToday()
  } catch (error) {
    if (await handleSafetyGateError(error)) return
    notify(error.message, 'error')
  }
})
function weekEndString(weekStart) {
  return shiftDate(weekStart, 6)
}

function weekRangeLabel(weekStart) {
  return `${weekStart} 至 ${weekEndString(weekStart)}`
}


// 说明由本地模板生成，不调用外部模型；历史模式使用快照中的设置。
function renderLocalPlanExplanation(plan, weekStart, historical) {
  const sessions = Array.isArray(plan.sessions) ? plan.sessions : []
  const sessionItems = sessions.map((session) => {
    const duration = session.duration_minutes ? ` · 约 ${escapeHtml(session.duration_minutes)} 分钟` : ""
    return `<li><b>${escapeHtml(session.day)} · ${escapeHtml(session.title)}${duration}</b><span>${escapeHtml(session.description)}</span></li>`
  }).join("")
  const sessionsMarkup = sessionItems
    ? `<ul class="explanation-session-list">${sessionItems}</ul>`
    : "<p>当前计划没有训练日条目。</p>"
  const days = Number.isFinite(Number(plan.days_per_week)) ? Number(plan.days_per_week) : sessions.length
  const setup = planSetupLabel(plan)
  const setupMarkup = setup ? `<p class="explanation-settings">本周设置：${escapeHtml(setup)}</p>` : ""
  const profileMarkup = plan.body_profile_context?.personal_profile_used
    ? '<p class="profile-plan-note">本次计划读取了个人档案：年龄段用于恢复提示；身高和体重用于建立后续变化对照。体脂率和腰围仅保存在档案中，不单独决定训练内容或强度。</p>'
    : '<p class="profile-plan-note">此历史计划没有记录使用个人身体档案。</p>'
  const scheduleMarkup = renderWeeklySchedule(plan)
  const title = historical ? `${weekRangeLabel(weekStart)} 的计划` : "本周计划"
  const scope = historical ? "这是已保存的历史计划，仅供回看，不代表本周训练建议。" : "以下内容根据本周当前计划整理。"
  const scheduleTitle = historical ? "当周安排" : "本周安排"
  $("#plan-explanation").innerHTML = `
    <p class="explanation-lead">${escapeHtml(title)}：围绕“${escapeHtml(plan.focus)}”安排，共 ${escapeHtml(days)} 天训练。${escapeHtml(scope)}</p>
    ${setupMarkup}
    ${profileMarkup}
    ${scheduleMarkup}
    <div class="explanation-block"><h4>${scheduleTitle}</h4>${sessionsMarkup}</div>
    <div class="explanation-block"><h4>执行时可以留意</h4><ul><li>开始前先查看计划中的训练内容和动作说明，按自己能够控制的节奏进行。</li><li>计划是通用模板，不要求为了补上未完成的训练而临时加量。</li><li>如果训练中出现明显不适，请停止训练；症状严重、持续或加重时，及时寻求专业帮助。</li></ul></div>
    <p class="explanation-source">说明来源：本地固定模板；未发送到外部模型服务。</p>
  `
}

// 把已加载的周计划快照绘制成列表，不修改当前周摘要。
function renderPlanHistory() {
  const target = $('#plan-history-list')
  const loadMore = $('#load-more-plans')
  loadMore.classList.toggle('hidden', !historyCursor)
  if (!planHistory.length) {
    target.className = 'plan-history-list empty-state'
    target.innerHTML = '<p>还没有可查看的已保存周计划。</p>'
    return
  }
  target.className = 'plan-history-list'
  target.innerHTML = planHistory.map((item) => {
    const weekStart = item.week_start
    const isCurrent = weekStart === historyCurrentWeekStart
    const isSelected = weekStart === selectedPlanWeek
    const plan = item.week_plan || {}
    const badge = isCurrent ? '本周' : '历史'
    return `<button class="plan-history-item${isSelected ? ' selected' : ''}" type="button" data-week-start="${escapeHtml(weekStart)}" aria-pressed="${isSelected}"><span class="plan-history-top"><b>${escapeHtml(weekRangeLabel(weekStart))}</b><span class="tag${isCurrent ? '' : ' history-tag'}">${badge}</span></span><span class="plan-history-meta">${escapeHtml(plan.focus)} · 每周 ${escapeHtml(plan.days_per_week)} 天</span><span class="plan-history-saved">保存时间：${escapeHtml(item.saved_at)}</span></button>`
  }).join('')
}

// 清空计划列表和预览，避免筛查未通过后残留先前加载的计划。
function clearPlanViews(resultMessage, summaryMessage, explanationMessage, historyMessage) {
  selectedPlanWeek = null
  planHistory = []
  historyCursor = null
  $('#plan-result').className = 'empty-state'
  $('#plan-result').textContent = resultMessage
  $('#plan-summary').className = 'empty-state'
  $('#plan-summary').textContent = summaryMessage
  $('#plan-explanation').innerHTML = `<div class="empty-state"><p>${escapeHtml(explanationMessage)}</p></div>`
  const history = $('#plan-history-list')
  history.className = 'plan-history-list empty-state'
  history.textContent = historyMessage
  $('#load-more-plans').classList.add('hidden')
}

function hidePlanForSafety(message) {
  showDailySignalForm()
  clearPlanViews(
    message,
    '完成安全筛查后，才可查看或生成本周计划。',
    '请先完成安全筛查。',
    '完成安全筛查后，才可查看已保存计划。',
  )
}

function hidePlanForUnavailable(message) {
  showDailySignalForm()
  clearPlanViews(
    `安全状态或数据库暂时不可用：${message}`,
    '安全状态或数据库暂时不可用，计划内容已隐藏。',
    '请恢复服务后刷新状态，再查看计划。',
    '安全状态或数据库暂时不可用，历史计划已隐藏。',
  )
}
function renderWeeklySchedule(plan) {
  if (!Array.isArray(plan.training_weekdays)) return ""
  const trainingDays = new Set(plan.training_weekdays.map(Number))
  const weekdayCards = WEEKDAY_LABELS.map((label, index) => {
    const isTrainingDay = trainingDays.has(index + 1)
    const dayClass = isTrainingDay ? "training-day" : "rest-day"
    const dayType = isTrainingDay ? "训练" : "休息"
    return `<div class="weekday-card ${dayClass}"><b>${label}</b><span>${dayType}</span></div>`
  }).join("")
  return `<div class="week-schedule" role="group" aria-label="本周训练与休息日">${weekdayCards}</div>`
}

function renderPlan(plan, savedAt, options = {}) {
  const sessions = Array.isArray(plan.sessions) ? plan.sessions : []
  const weekStart = options.weekStart || historyCurrentWeekStart || mondayFor(localDateString())
  const historical = options.historical === true
  selectedPlanWeek = weekStart
  const period = weekRangeLabel(weekStart)
  const banner = historical
    ? `<div class="history-plan-banner">历史计划，仅供回看 · ${escapeHtml(period)}，不代表本周训练建议。</div>`
    : `<div class="history-plan-banner current-plan-banner">当前周计划 · ${escapeHtml(period)}</div>`
  const saveNote = historical
    ? "这是已保存的历史计划，仅供回看。"
    : `本周计划已保存到本机 PostgreSQL。${savedAt ? `保存时间：${escapeHtml(savedAt)}` : ""} 服务重启后，完成安全筛查即可恢复。`
  const setup = planSetupLabel(plan)
  const setupMarkup = setup ? `<p class="fine-print">本周设置：${escapeHtml(setup)}</p>` : ""
  const scheduleMarkup = renderWeeklySchedule(plan)
  $("#plan-result").className = "plan-result"
  $("#plan-result").innerHTML = `${banner}${scheduleMarkup}<div class="plan-meta"><span>${escapeHtml(plan.focus)}</span><span>每周 ${escapeHtml(plan.days_per_week)} 天</span></div>${setupMarkup}<div class="session-list">${sessions.map((session, index) => {
    const duration = session.duration_minutes ? ` · 约 ${escapeHtml(session.duration_minutes)} 分钟` : ""
    return `<article class="session"><span class="session-index">0${index + 1}</span><div><b>${escapeHtml(session.day)} · ${escapeHtml(session.title)}${duration}</b><p>${escapeHtml(session.description)}</p></div></article>`
  }).join("")}</div><p class="fine-print">${escapeHtml(plan.notice)}</p><p class="plan-storage-note">${escapeHtml(saveNote)}</p>`
  renderLocalPlanExplanation(plan, weekStart, historical)
  if (!historical) {
    $("#plan-summary").className = "plan-summary-mini"
    $("#plan-summary").innerHTML = `<b>${escapeHtml(plan.focus)} · 每周 ${escapeHtml(plan.days_per_week)} 天</b><p>${setup ? `${escapeHtml(setup)}<br>` : ""}${sessions.map((session) => escapeHtml(session.title)).join(" / ")}</p><button class="text-button" data-goto="plan">查看计划 →</button>`
    $("#plan-summary [data-goto]").addEventListener("click", () => showPage("plan"))
  }
}

function showNoCurrentPlan() {
  selectedPlanWeek = null
  $('#plan-result').className = 'empty-state'
  $('#plan-result').innerHTML = '<div class="empty-icon">✳</div><p>本周还没有保存的计划。请选择训练星期，再填写目标、经验、器械和时长。</p>'
  $('#plan-summary').className = 'empty-state'
  $('#plan-summary').innerHTML = '<p>本周尚未生成计划。</p><button class="text-button" data-goto="plan">前往周计划 →</button>'
  $('#plan-summary [data-goto]').addEventListener('click', () => showPage('plan'))
  $('#plan-explanation').innerHTML = '<div class="empty-state"><p>生成本周计划后，这里会说明本周安排概况和通用执行提醒。你也可以从历史列表选择已保存计划回看。</p></div>'
}

// 处理安全门禁和数据库错误；遇到不确定状态时清空前端已加载的计划。
async function handleSafetyGateError(error) {
  if (error.status === 503) {
    safetyStatus = 'ask'
    screeningDate = null
    updateSafetyUi()
    hidePlanForUnavailable(error.message)
    return true
  }
  if (error.status !== 409 && error.status !== 423) return false
  safetyStatus = error.status === 423 ? 'stop' : 'ask'
  screeningDate = null
  updateSafetyUi()
  hidePlanForSafety(error.message)
  return true
}
async function loadPlanHistory(reset = true) {
  if (safetyStatus !== 'clear' || historyLoading) return
  if (reset) {
    planHistory = []
    historyCursor = null
    const target = $('#plan-history-list')
    target.className = 'plan-history-list empty-state'
    target.textContent = '正在读取已保存计划…'
    $('#load-more-plans').classList.add('hidden')
  }
  historyLoading = true
  const params = new URLSearchParams({ limit: '20' })
  if (!reset && historyCursor) params.set('before_week_start', historyCursor)
  try {
    const result = await api(`/api/plan/history?${params.toString()}`)
    if (safetyStatus !== 'clear') return
    historyCurrentWeekStart = result.current_week_start
    const knownWeeks = new Set(planHistory.map((item) => item.week_start))
    planHistory = planHistory.concat((result.items || []).filter((item) => !knownWeeks.has(item.week_start)))
    historyCursor = result.next_before_week_start
    renderPlanHistory()
  } catch (error) {
    if (await handleSafetyGateError(error)) return
    if (selectedPlanWeek && selectedPlanWeek !== historyCurrentWeekStart) {
      selectedPlanWeek = null
      $('#plan-result').className = 'empty-state'
      $('#plan-result').textContent = '历史计划暂时无法读取，请重试。'
      $('#plan-explanation').innerHTML = '<div class="empty-state"><p>历史计划暂时无法读取，请重试后查看。</p></div>'
    }
    const target = $('#plan-history-list')
    target.className = 'plan-history-list empty-state'
    target.innerHTML = `<p>${escapeHtml(error.message)}</p><button class="text-button" id="retry-plan-history" type="button">重试</button>`
    $('#retry-plan-history').addEventListener('click', () => loadPlanHistory(true))
  } finally {
    historyLoading = false
  }
}

$('#plan-history-list').addEventListener('click', (event) => {
  const button = event.target.closest('[data-week-start]')
  if (!button || safetyStatus !== 'clear') return
  const item = planHistory.find((entry) => entry.week_start === button.dataset.weekStart)
  if (!item) return
  const historical = item.week_start !== historyCurrentWeekStart
  renderPlan(item.week_plan, item.saved_at, {
    weekStart: item.week_start,
    historical,
  })
  renderPlanHistory()
})

$('#refresh-plan-history').addEventListener('click', () => loadPlanHistory(true))
$('#load-more-plans').addEventListener('click', () => loadPlanHistory(false))

// 先恢复当前周计划，再读取第一页历史记录；异步返回后再次确认安全状态。
async function refreshCurrentPlan() {
  try {
    const result = await api('/api/plan/current')
    if (safetyStatus !== 'clear') return
    historyCurrentWeekStart = result.week_start
    if (result.week_plan) renderPlan(result.week_plan, result.saved_at, { weekStart: result.week_start })
    else showNoCurrentPlan()
  } catch (error) {
    if (await handleSafetyGateError(error)) return
    $('#plan-result').className = 'empty-state'
    $('#plan-result').textContent = error.message
  }
  await loadPlanHistory(true)
}

// 星期选择数量直接决定每周训练天数；超过 6 天时撤销本次勾选并提示至少保留一天休息。
$$('input[name="training_weekdays"]').forEach((input) => {
  input.addEventListener('change', () => {
    planFormEdited = true
    if (selectedTrainingWeekdays().length > 6) {
      input.checked = false
      notify('每周最多选择 6 个训练日，请至少保留 1 天休息。', 'error')
    }
    updateWeekdayCount()
  })
})
updateWeekdayCount()

// “仅自重”与其他器械互斥；同时保留后端校验，避免绕过页面直接提交非法组合。
$$('input[name="equipment"]').forEach((input) => {
  input.addEventListener('change', () => {
    if (input.value === 'bodyweight_only' && input.checked) {
      $$('input[name="equipment"]').forEach((item) => {
        if (item.value !== 'bodyweight_only') item.checked = false
      })
    } else if (input.checked) {
      const bodyweight = $('input[name="equipment"][value="bodyweight_only"]')
      bodyweight.checked = false
    }
  })
})
$('#plan-form').addEventListener('input', () => { planFormEdited = true })
$('#plan-form').addEventListener('change', () => { planFormEdited = true })
$('#plan-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const form = event.currentTarget
  const button = form.querySelector('[type="submit"]')
  if (!planPreferencesLoaded && !planPreferencesLoading) await loadPlanPreferences()
  if (planPreferencesLoading) return notify('正在读取上次保存的设置，请稍后再生成。', 'error')
  if (safetyStatus !== 'clear') return notify('请先完成安全筛查，再生成周计划。', 'error')
  const data = new FormData(form)
  const trainingWeekdays = selectedTrainingWeekdays()
  if (!trainingWeekdays.length) return notify('请至少选择一个训练星期。', 'error')
  const equipment = data.getAll('equipment')
  if (!equipment.length) return notify('请至少选择一种可用器械。', 'error')
  if (equipment.includes('bodyweight_only') && equipment.length > 1) {
    return notify('“仅自重”不能与其他器械同时选择。', 'error')
  }
  const payload = {
    goal: data.get('goal'),
    days_per_week: trainingWeekdays.length,
    training_weekdays: trainingWeekdays,
    experience_level: data.get('experience_level'),
    equipment,
    session_minutes: Number(data.get('session_minutes')),
  }
  button.disabled = true
  try {
    const result = await api('/api/plan', { method: 'POST', body: JSON.stringify(payload) })
    if (safetyStatus !== 'clear') return
    planPreferencesLoaded = true
    historyCurrentWeekStart = result.week_start
    renderPlan(result.week_plan, result.saved_at, { weekStart: result.week_start })
    notify(result.message || '本周计划已保存。')
    await loadPlanHistory(true)
  } catch (error) {
    if (await handleSafetyGateError(error)) return
    notify(error.message, 'error')
  } finally {
    button.disabled = false
  }
})
$('#log-form').training_date.value = localDateString()
$('#log-form [name="completion"]').addEventListener('change', (event) => {
  $('#skip-reason-wrap').classList.toggle('hidden', event.target.value !== 'skipped')
})

$('#log-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const form = event.currentTarget
  const data = new FormData(form)
  const payload = { training_date: data.get('training_date'), completion: data.get('completion') }
  if (data.get('rpe')) payload.rpe = Number(data.get('rpe'))
  if (data.get('skip_reason')) payload.skip_reason = data.get('skip_reason')
  if (data.get('note')) payload.note = data.get('note')
  try {
    await api('/api/log', { method: 'POST', body: JSON.stringify(payload) })
    form.reset()
    $('#log-form').training_date.value = localDateString()
    $('#skip-reason-wrap').classList.add('hidden')
    notify('训练记录已保存。')
    await refreshLogs()
    refreshWeeklyReview()
  } catch (error) {
    if (await handleSafetyGateError(error)) return
    notify(error.message, 'error')
  }
})

// 训练记录与周回顾共用这些中文标签和本地日期工具。
const completionLabels = { completed: '按计划完成', partial: '部分完成', skipped: '未进行训练' }
const reasonLabels = { no_time: '没时间', too_tired: '太累', discomfort: '身体不适', other: '其他' }
async function refreshLogs() {
  const target = $('#logs-list')
  try {
    const result = await api('/api/logs')
    if (!result.items.length) {
      target.className = 'empty-state'
      target.innerHTML = '<div class="empty-icon">↗</div><p>还没有训练记录。</p>'
      return
    }
    target.className = 'logs-list'
    target.innerHTML = result.items.map((item) => `<article class="log-entry"><div><b>${escapeHtml(item.training_date)} · ${escapeHtml(completionLabels[item.completion])}</b><p>${item.rpe ? `RPE ${escapeHtml(item.rpe)}` : '未填 RPE'}${item.skip_reason ? ` · ${escapeHtml(reasonLabels[item.skip_reason])}` : ''}</p>${item.note ? `<p>${escapeHtml(item.note)}</p>` : ''}</div><span class="log-dot ${item.completion}"></span></article>`).join('')
  } catch (error) {
    if (await handleSafetyGateError(error)) return
    target.textContent = error.message
  }
}
$('#refresh-logs').addEventListener('click', refreshLogs)


const readinessLabels = { good: '状态不错', okay: '一般', poor: '状态较差' }
const weekdayLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
function localDateString(value = new Date()) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
function mondayFor(value) {
  const [year, month, day] = value.split('-').map(Number)
  const date = new Date(year, month - 1, day)
  date.setDate(date.getDate() - ((date.getDay() + 6) % 7))
  return localDateString(date)
}
function shiftDate(value, days) {
  const [year, month, day] = value.split('-').map(Number)
  const date = new Date(year, month - 1, day)
  date.setDate(date.getDate() + days)
  return localDateString(date)
}
// 日期变化时先清空已展示计划，再向服务端确认新一天的筛查状态。
function expireScreeningForNewDay() {
  if (safetyStatus !== 'clear' || !screeningDate || screeningDate === localDateString()) return
  screeningDate = null
  safetyStatus = 'ask'
  updateSafetyUi()
  hidePlanForSafety('新的一天开始，请重新完成安全筛查。')
  refreshToday()
}

document.addEventListener('visibilitychange', () => {
  if (!document.hidden) expireScreeningForNewDay()
})
setInterval(expireScreeningForNewDay, 30 * 1000)
$('#review-date').value = localDateString()
$('#review-date').addEventListener('change', (event) => {
  if (event.target.value) refreshWeeklyReview()
})
$('#previous-week').addEventListener('click', () => {
  $('#review-date').value = shiftDate(mondayFor($('#review-date').value || localDateString()), -7)
  refreshWeeklyReview()
})
$('#next-week').addEventListener('click', () => {
  $('#review-date').value = shiftDate(mondayFor($('#review-date').value || localDateString()), 7)
  refreshWeeklyReview()
})

$('#current-week').addEventListener('click', () => {
  $('#review-date').value = localDateString()
  refreshWeeklyReview()
})

// 周回顾显示服务端汇总；缺失数据保持为未记录，不在浏览器端猜测。
async function refreshWeeklyReview() {
  const stats = $('#review-stats')
  const daysTarget = $('#review-days')
  const selectedDate = $('#review-date').value || localDateString()
  try {
    const result = await api(`/api/review/week?week_of=${encodeURIComponent(selectedDate)}`)
    $('#review-date').min = result.registration_date
    $('#review-range').textContent = `${result.week_start} 至 ${result.week_end} · 可查看自 ${result.registration_date}`
    $('#previous-week').disabled = shiftDate(result.week_start, -1) < result.registration_date
    const summary = result.summary
    const statItems = [
      ['日志条数', `${summary.session_count} 条`],
      ['按计划完成', `${summary.completed_count} 次`],
      ['部分完成', `${summary.partial_count} 次`],
      ['未进行', `${summary.skipped_count} 次`],
      ['平均 RPE', summary.average_rpe == null ? `未记录（${summary.rpe_count} 条）` : `${summary.average_rpe} / 10（${summary.rpe_count} 条）`],
    ]
    stats.innerHTML = statItems.map(([label, value]) => `<article class="panel review-stat"><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b></article>`).join('')
    daysTarget.innerHTML = result.days.map((day, index) => {
      const signal = day.signal
      const stateText = day.before_registration ? '注册前：不适用' : signal
        ? `${escapeHtml(readinessLabels[signal.readiness] || '未知')} · 睡眠 ${signal.sleep_hours == null ? '未记录' : `${escapeHtml(signal.sleep_hours)} 小时`} · 静息心率 ${signal.resting_hr == null ? '未记录' : `${escapeHtml(signal.resting_hr)} 次/分`}`
        : '状态：未记录'
      const logHtml = day.before_registration ? '<div class="review-missing">注册前：不适用</div>' : day.logs.length
        ? day.logs.map((log) => `<div class="review-log"><b>${escapeHtml(completionLabels[log.completion] || '未知记录')}</b><span>${log.rpe == null ? 'RPE 未记录' : `RPE ${escapeHtml(log.rpe)}`}${log.skip_reason ? ` · ${escapeHtml(reasonLabels[log.skip_reason] || '')}` : ''}</span>${log.note ? `<p>${escapeHtml(log.note)}</p>` : ''}</div>`).join('')
        : '<div class="review-missing">训练日志：未记录</div>'
      return `<article class="panel review-day"><div class="review-day-head"><b>${weekdayLabels[index]} · ${escapeHtml(day.date)}</b></div><p class="review-signal">${stateText}</p><div class="review-log-list">${logHtml}</div></article>`
    }).join('')
  } catch (error) {
    if (await handleSafetyGateError(error)) return
    stats.innerHTML = ''
    daysTarget.innerHTML = `<article class="panel review-error">${escapeHtml(error.message)}</article>`
  }
}

// 根据 loading / ask / clear / stop 状态，只显示对应的筛查或暂停界面。
function updateSafetyUi() {
  const loading = safetyStatus === 'loading'
  const cleared = safetyStatus === 'clear'
  const held = safetyStatus === 'stop'
  $('#safety-loading').classList.toggle('hidden', !loading)
  $('#safety-complete').classList.toggle('hidden', !cleared)
  $('#resolution-form').classList.toggle('hidden', !held)
  $('#safety-form').classList.toggle('hidden', loading || cleared || held)
}

$('#restart-safety-check').addEventListener('click', async (event) => {
  const button = event.currentTarget
  button.disabled = true
  try {
    const result = await api('/api/safety-check', {
      method: 'POST',
      body: JSON.stringify({ completed: false, no_symptoms: false, symptoms: [] }),
    })
    safetyStatus = result.status
    screeningDate = null
    $('#safety-form').reset()
    updateSafetyUi()
    hidePlanForSafety('请完成重新筛查，再查看周计划。')
  } catch (error) {
    if (await handleSafetyGateError(error)) return
    notify(error.message, 'error')
  } finally {
    button.disabled = false
  }
})

$('#no-symptoms').addEventListener('change', (event) => {
  if (event.target.checked) {
    $$('input[name="symptoms"]').forEach((input) => { input.checked = false })
  }
})
$$('input[name="symptoms"]').forEach((input) => input.addEventListener('change', () => {
  if (input.checked) $('#no-symptoms').checked = false
}))

$('#safety-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const data = new FormData(event.currentTarget)
  const symptoms = data.getAll('symptoms')
  try {
    const result = await api('/api/safety-check', {
      method: 'POST',
      body: JSON.stringify({
        completed: Boolean(data.get('completed')),
        no_symptoms: Boolean(data.get('no_symptoms')),
        symptoms,
      }),
    })
    safetyStatus = result.status
    screeningDate = result.status === 'clear' ? (result.screening_date || localDateString()) : null
    updateSafetyUi()
    if (result.status !== "clear") hidePlanForSafety(result.message)
    notify(result.message, result.status === 'stop' || result.status === 'ask' ? 'error' : 'info')
    await refreshToday()
  } catch (error) {
    if (await handleSafetyGateError(error)) return
    notify(error.message, 'error')
  }
})

$('#resolution-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const form = event.currentTarget
  const data = new FormData(form)
  try {
    const result = await api('/api/safety-resolution', {
      method: 'POST',
      body: JSON.stringify({
        confirmed_recovery: Boolean(data.get('confirmed_recovery')),
        followed_professional_advice: Boolean(data.get('followed_professional_advice')),
      }),
    })
    safetyStatus = 'ask'
    screeningDate = null
    form.reset()
    updateSafetyUi()
    notify(result.message)
    await refreshToday()
  } catch (error) {
    if (await handleSafetyGateError(error)) return
    notify(error.message, 'error')
  }
})

// 多标签页共享浏览器会话；账号切换时刷新其他标签，清除前一账号的页面缓存。
window.addEventListener('storage', (event) => {
  if (event.key === 'fitnessCoachAuthChanged') window.location.reload()
})
function broadcastAuthChange() {
  try { localStorage.setItem('fitnessCoachAuthChanged', String(Date.now())) } catch { /* 存储不可用时当前标签仍会自行刷新 */ }
}

let authMode = "login"

function setAuthMode(mode) {
  authMode = mode
  const register = mode === "register"
  $$('[data-auth-mode]').forEach((button) => {
    const selected = button.dataset.authMode === mode
    button.classList.toggle('active', selected)
    button.setAttribute('aria-selected', String(selected))
  })
  $('#display-name-field').classList.toggle('hidden', !register)
  $('#password-confirm-field').classList.toggle('hidden', !register)
  $('#auth-form').elements.password_confirm.required = register
  $('#auth-form').elements.password.autocomplete = register ? 'new-password' : 'current-password'
  $('#auth-title').textContent = register ? '创建你的训练账号' : '欢迎回来'
  $('#auth-description').textContent = register ? '注册后会为你单独保存档案、训练计划和记录。' : '登录后查看你自己的身体档案、训练计划和记录。'
  $('#auth-submit').textContent = register ? '注册并进入' : '登录'
  $('#auth-error').textContent = ''
}

function revealAccount(user) {
  activeAccount = user
  $('#auth-gate').classList.add('hidden')
  $('#account-name').textContent = `${user.display_name} · ${user.username}`
  $('#account-name').classList.remove('hidden')
  $('#logout-button').classList.remove('hidden')
  $('#user-center-display-name').textContent = user.display_name
  $('#user-center-username').textContent = `账号：${user.username}`
  $('#profile-account-tag').textContent = '已登录'
}

async function startAuthenticatedApplication() {
  if (applicationStarted) return
  applicationStarted = true
  refreshToday()
  refreshLogs()
  loadBodyProfile({ promptIfNeeded: true })
}

async function checkAuthentication() {
  try {
    const result = await api('/api/auth/me')
    revealAccount(result.user)
    await startAuthenticatedApplication()
  } catch (error) {
    if (error.status === 401) {
      activeAccount = null
      $('#auth-gate').classList.remove('hidden')
      $('#auth-form').elements.username.focus()
      return
    }
    $('#auth-error').textContent = error.message || '连接服务器失败，请确认应用服务仍在运行。'
  }
}

$$('[data-auth-mode]').forEach((button) => button.addEventListener('click', () => setAuthMode(button.dataset.authMode)))
$('#auth-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const form = event.currentTarget
  const data = new FormData(form)
  const username = String(data.get('username') || '').trim()
  const password = String(data.get('password') || '')
  if (authMode === 'register' && password !== data.get('password_confirm')) {
    $('#auth-error').textContent = '两次输入的密码不一致。'
    return
  }
  const payload = { username, password }
  if (authMode === 'register' && String(data.get('display_name') || '').trim()) {
    payload.display_name = String(data.get('display_name')).trim()
  }
  const submitButton = $('#auth-submit')
  submitButton.disabled = true
  $('#auth-error').textContent = ''
  try {
    await api(authMode === 'register' ? '/api/auth/register' : '/api/auth/login', {
      method: 'POST', body: JSON.stringify(payload),
    })
    broadcastAuthChange()
    window.location.reload()
  } catch (error) {
    $('#auth-error').textContent = error.message
  } finally {
    submitButton.disabled = false
  }
})
$('#logout-button').addEventListener('click', async () => {
  try {
    await api('/api/auth/logout', { method: 'POST' })
    broadcastAuthChange()
    window.location.reload()
  } catch (error) {
    notify(error.message, 'error')
  }
})

checkAuthentication()

