// 浏览器端交互入口：请求 FastAPI、更新页面，并跟踪今日确认状态和计划浏览状态。
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
let planRecommendationsLoaded = false
let planRecommendationsLoading = false
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


// 统一封装 fetch，把服务端错误转换为带 HTTP 状态码的异常。
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
    loadPlanPreferences().then(loadPlanRecommendations)
    refreshCurrentPlan()
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
  $('#body-profile-modal').querySelector('.profile-modal-history').classList.toggle('hidden', onboarding)
  $('#profile-modal-storage-note').classList.toggle('hidden', onboarding)
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
      return true
    }
    form.elements.age_band.value = profile.age_band
    form.elements.height_cm.value = profile.height_cm
    form.elements.weight_kg.value = profile.weight_kg
    form.elements.target_weight_kg.value = profile.target_weight_kg ?? ''
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
    return true
  } catch (error) {
    notify(error.message, 'error')
    return false
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
    target_weight_kg: optionalNumber('target_weight_kg'),
  }
  try {
    const result = await api('/api/body-profile', { method: 'PUT', body: JSON.stringify(payload) })
    closeBodyProfileModal({ skipped: true })
    planRecommendationsLoaded = false
    await loadBodyProfile()
    if ($('#page-plan').classList.contains('active')) loadPlanRecommendations()
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
    planRecommendationsLoaded = false
    notify(result.message)
    await loadBodyProfile()
    if ($('#page-plan').classList.contains('active')) loadPlanRecommendations()
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

// 只在首次进入计划页时回填偏好，避免覆盖用户正在编辑的值。
const TRAINING_GOAL_OPTIONS = [
  { value: 'fitness', title: '综合体能', summary: '力量练习与轻松有氧交替安排。' },
  { value: 'strength', title: '力量基础', summary: '以熟悉、安全的力量练习作为主要方向。' },
  { value: 'fat_loss', title: '提升日常活动', summary: '从可持续的日常活动和基础力量开始。' },
]

function updateTrainingGoalCards() {
  const selectedGoal = $('#plan-form').elements.goal.value
  $('#plan-goal-options').querySelectorAll('[data-plan-goal]').forEach((card) => {
    const selected = card.dataset.planGoal === selectedGoal
    card.classList.toggle('selected', selected)
    card.setAttribute('aria-pressed', String(selected))
    card.querySelector('.goal-selected-label').textContent = selected ? '已选择' : '选择方向'
  })
}

async function loadPlanRecommendations() {
  if (planRecommendationsLoaded || planRecommendationsLoading) return
  planRecommendationsLoading = true
  const context = $('#plan-recommendation-context')
  const options = $('#plan-goal-options')
  const fillProfile = $('#plan-fill-profile')
  try {
    const [profileResult, preferencesResult, currentResult] = await Promise.all([
      api('/api/body-profile'),
      api('/api/plan/preferences'),
      api('/api/plan/current'),
    ])
    const profile = profileResult.profile
    const preferences = preferencesResult.preferences
    if (!profile) {
      context.textContent = '填写身高、体重和年龄段后，我会结合你的档案展示训练方向。'
      options.innerHTML = ''
      fillProfile.classList.remove('hidden')
      planRecommendationsLoaded = true
      return
    }
    fillProfile.classList.add('hidden')
    const currentWeight = Number(profile.weight_kg)
    const targetWeight = profile.target_weight_kg == null ? null : Number(profile.target_weight_kg)
    const bmi = profile.age_band === 'under_18' ? null : currentWeight / ((Number(profile.height_cm) / 100) ** 2)
    const profileLabel = '档案：身高 ' + profile.height_cm + ' cm · 当前体重 ' + currentWeight.toFixed(1) + ' kg'
    const bmiLabel = bmi == null ? '未成年人不使用成人 BMI 参考值' : '成人 BMI 参考值 ' + bmi.toFixed(1)
    // 未成年人以均衡训练为推荐起点，不用体重目标或成人 BMI 推断方向。
    const isMinor = profile.age_band === 'under_18'
    let recommendation = preferences.goal || 'fitness'
    let reason
    if (isMinor) {
      recommendation = 'fitness'
      reason = '未满 18 岁时，不根据体重目标或成人 BMI 推荐减重方向。建议以均衡体能和循序渐进的熟悉活动为起点。'
    } else if (targetWeight != null && targetWeight < currentWeight - 0.2) {
      recommendation = 'fat_loss'
      reason = '你设置的体重目标低于当前记录。可以从提升日常活动开始，逐步建立稳定习惯；计划不会推算减重速度。'
    } else if (targetWeight != null && targetWeight > currentWeight + 0.2) {
      reason = '你设置了高于当前记录的体重目标。训练方向仍由你选择，系统不会仅根据体重推断增重或饮食方案。'
    } else if (targetWeight != null) {
      recommendation = 'fitness'
      reason = '当前记录接近你自设的体重目标。综合体能可作为均衡起点，你也可以选择其他方向。'
    } else if (currentResult.week_plan?.goal) {
      recommendation = currentResult.week_plan.goal
      reason = '你还没有设置体重目标。这里先沿用你本周选择的方向，也可以根据当前身体档案重新选择。'
    } else {
      reason = '你还没有设置体重目标。综合体能是一个均衡起点；身高、体重和 BMI 用于查看与回顾，不单独决定训练方向。'
    }
    const currentWeekGoal = currentResult.week_plan?.goal
    const selectedGoal = currentWeekGoal || recommendation
    if (!planFormEdited) $('#plan-form').elements.goal.value = selectedGoal
    const contextParts = [profileLabel, bmiLabel]
    if (!isMinor && targetWeight != null) contextParts.push('自设目标 ' + targetWeight.toFixed(1) + ' kg')
    context.textContent = contextParts.join('　｜　') + '。' + reason
    options.innerHTML = TRAINING_GOAL_OPTIONS.map((item) => {
      const recommended = item.value === recommendation
      const selected = item.value === $('#plan-form').elements.goal.value
      return '<button class="plan-goal-card' + (selected ? ' selected' : '') + '" type="button" data-plan-goal="' + item.value + '" aria-pressed="' + String(selected) + '">'
        + '<span class="plan-goal-card-top"><b>' + item.title + '</b>' + (recommended ? '<i>推荐起点</i>' : '') + '</span>'
        + '<span class="plan-goal-card-summary">' + item.summary + '</span>'
        + '<span class="goal-selected-label">' + (selected ? '已选择' : '选择方向') + '</span></button>'
    }).join('')
    planRecommendationsLoaded = true
  } catch (error) {
    context.textContent = error.message || '暂时无法读取身体档案或训练偏好，请稍后重试。'
  } finally {
    planRecommendationsLoading = false
  }
}

$('#plan-goal-options').addEventListener('click', (event) => {
  const card = event.target.closest('[data-plan-goal]')
  if (!card) return
  $('#plan-form').elements.goal.value = card.dataset.planGoal
  planFormEdited = true
  updateTrainingGoalCards()
  $('#plan-form').elements.goal.dispatchEvent(new Event('change', { bubbles: true }))
})
$('#plan-fill-profile').addEventListener('click', async () => {
  if (await loadBodyProfile()) openBodyProfileModal()
})

async function loadPlanPreferences() {
  if (planPreferencesLoaded || planPreferencesLoading) return
  planPreferencesLoading = true
  try {
    const result = await api("/api/plan/preferences")
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

// 前端根据今日接口同步确认状态；周计划和历史计划不受今日确认结果限制。
async function refreshToday() {
  const card = $('#today-card')
  try {
    const result = await api('/api/today')
    const [label, detail] = levelLabel(result.level)
    const isRestDay = result.level === 'rest_day'
    safetyStatus = result.level === 'ask' ? 'ask' : result.level === 'stop' ? 'stop' : 'clear'
    screeningDate = result.screening_date || null
    $('#safety-check-module').classList.toggle('hidden', isRestDay)
    updateSafetyUi()
    if (isRestDay) {
      $('#signal-form').hidden = true
      $('#rest-day-signal-note').textContent = '今天是计划休息日，无需填写训练状态。'
      $('#rest-day-signal-note').classList.remove('hidden')
      $('#signal-panel-title').textContent = '今天是计划休息日'
    } else if (result.level === 'stop') {
      $('#signal-form').hidden = true
      $('#rest-day-signal-note').textContent = '今天的训练建议已暂停，无需填写训练状态。'
      $('#rest-day-signal-note').classList.remove('hidden')
      $('#signal-panel-title').textContent = '今天的训练建议已暂停'
    } else if (result.level === 'ask') {
      $('#signal-form').hidden = true
      $('#rest-day-signal-note').textContent = '请先确认今天的身体感受，再记录训练状态。'
      $('#rest-day-signal-note').classList.remove('hidden')
      $('#signal-panel-title').textContent = '确认身体状态后再记录'
    } else {
      showDailySignalForm()
    }
    const scheduleMarkup = result.level === 'normal' || isRestDay ? renderTodaySchedule(result.today_schedule) : ''
    card.className = `status-card status-${result.level}`
    card.innerHTML = `<div class="status-top"><span class="status-pill"><i></i>${escapeHtml(label)}</span><span class="status-detail">${escapeHtml(detail)}</span></div><h3>${escapeHtml(result.message)}</h3><ul class="reason-list">${(result.reasons || []).map((reason) => `<li>${escapeHtml(reason)}</li>`).join('')}</ul>${scheduleMarkup}`
    card.querySelector('[data-goto="plan"]')?.addEventListener('click', () => showPage('plan'))
    await refreshCurrentPlan()
  } catch (error) {
    safetyStatus = 'loading'
    screeningDate = null
    updateSafetyUi()
    card.className = 'status-card status-ask'
    card.textContent = error.message
  }
}
$('#refresh-today').addEventListener('click', refreshToday)

// 用户输入的每日状态需要先完成今日身体感受确认。
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
function renderLocalPlanExplanation(plan, weekStart, historical, pausedWeekday = null) {
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
  const profileContext = plan.body_profile_context || {}
  const profileSummary = [
    profileContext.height_cm ? '身高 ' + escapeHtml(profileContext.height_cm) + ' cm' : '',
    profileContext.weight_kg ? '计划生成时体重 ' + escapeHtml(profileContext.weight_kg) + ' kg' : '',
    profileContext.target_weight_kg ? '自设目标 ' + escapeHtml(profileContext.target_weight_kg) + ' kg' : '',
  ].filter(Boolean).join(' · ')
  const profileMarkup = profileContext.personal_profile_used
    ? '<p class="profile-plan-note">本次计划读取了个人档案。' + (profileSummary ? '身体数据基线：' + profileSummary + '。' : '') + '这些数据用于进度对照；训练安排仍依据你的训练目标、经验、器械和时间，不会单凭 BMI 自动加量。</p>'
    : '<p class="profile-plan-note">此历史计划没有记录使用个人身体档案。</p>'
  const scheduleMarkup = renderWeeklySchedule(plan, pausedWeekday)
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

// 数据读取失败时清空计划列表和预览，避免页面保留过期内容。
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

function renderWeeklySchedule(plan, pausedWeekday = null) {
  if (!Array.isArray(plan.training_weekdays)) return ""
  const trainingDays = new Set(plan.training_weekdays.map(Number))
  const weekdayCards = WEEKDAY_LABELS.map((label, index) => {
    const weekday = index + 1
    const isPaused = weekday === pausedWeekday
    const isTrainingDay = trainingDays.has(weekday)
    const dayClass = isPaused ? "paused-day" : isTrainingDay ? "training-day" : "rest-day"
    const dayType = isPaused ? "今日暂停" : isTrainingDay ? "训练" : "休息"
    return `<div class="weekday-card ${dayClass}"><b>${label}</b><span>${dayType}</span></div>`
  }).join("")
  return `<div class="week-schedule" role="group" aria-label="本周训练与休息日">${weekdayCards}</div>`
}

function renderPlan(plan, savedAt, options = {}) {
  const weekStart = options.weekStart || historyCurrentWeekStart || mondayFor(localDateString())
  const historical = options.historical === true
  const todayParts = localDateString().split('-').map(Number)
  const todayWeekday = new Date(todayParts[0], todayParts[1] - 1, todayParts[2]).getDay() || 7
  const pauseToday = !historical && safetyStatus === 'stop' && weekStart === mondayFor(localDateString())
  const allSessions = Array.isArray(plan.sessions) ? plan.sessions : []
  const sessions = pauseToday ? allSessions.filter((session) => Number(session.weekday) !== todayWeekday) : allSessions
  selectedPlanWeek = weekStart
  const period = weekRangeLabel(weekStart)
  const banner = historical
    ? `<div class="history-plan-banner">历史计划，仅供回看 · ${escapeHtml(period)}，不代表本周训练建议。</div>`
    : `<div class="history-plan-banner current-plan-banner">当前周计划 · ${escapeHtml(period)}</div>`
  const saveNote = historical
    ? "这是已保存的历史计划，仅供回看。"
    : `本周计划已保存到本机 PostgreSQL。${savedAt ? `保存时间：${escapeHtml(savedAt)}` : ""} 服务重启后仍可查看，今日确认只影响当天训练安排。`
  const setup = planSetupLabel(plan)
  const setupMarkup = setup ? `<p class="fine-print">本周设置：${escapeHtml(setup)}</p>` : ""
  const scheduleMarkup = renderWeeklySchedule(plan, pauseToday ? todayWeekday : null)
  const pauseNote = pauseToday ? '<div class="safety-stop-note">今天的训练安排已暂停；本周其他安排仍可查看。</div>' : ''
  $("#plan-result").className = "plan-result"
  $("#plan-result").innerHTML = `${banner}${pauseNote}${scheduleMarkup}<div class="plan-meta"><span>${escapeHtml(plan.focus)}</span><span>每周 ${escapeHtml(plan.days_per_week)} 天</span></div>${setupMarkup}<div class="session-list">${sessions.map((session, index) => {
    const duration = session.duration_minutes ? ` · 约 ${escapeHtml(session.duration_minutes)} 分钟` : ""
    return `<article class="session"><span class="session-index">0${index + 1}</span><div><b>${escapeHtml(session.day)} · ${escapeHtml(session.title)}${duration}</b><p>${escapeHtml(session.description)}</p></div></article>`
  }).join("")}</div><p class="fine-print">${escapeHtml(plan.notice)}</p><p class="plan-storage-note">${escapeHtml(saveNote)}</p>`
  renderLocalPlanExplanation(pauseToday ? { ...plan, sessions } : plan, weekStart, historical, pauseToday ? todayWeekday : null)
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

// 处理今日状态冲突和数据库错误；今日暂停时保留周计划与历史记录。
async function handleSafetyGateError(error) {
  if (error.status !== 409 && error.status !== 423) return false
  safetyStatus = error.status === 423 ? 'stop' : 'ask'
  screeningDate = null
  updateSafetyUi()
  await refreshToday()
  return true
}
async function loadPlanHistory(reset = true) {
  if (historyLoading) return
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
  if (!button) return
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
$('#plan-form').elements.goal.addEventListener('change', updateTrainingGoalCards)
$('#plan-form').addEventListener('input', () => { planFormEdited = true })
$('#plan-form').addEventListener('change', () => { planFormEdited = true })
$('#plan-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const form = event.currentTarget
  const button = form.querySelector('[type="submit"]')
  if (!planPreferencesLoaded && !planPreferencesLoading) await loadPlanPreferences()
  if (planPreferencesLoading) return notify('正在读取上次保存的设置，请稍后再生成。', 'error')

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
async function refreshLogPlanContext() {
  const target = $('#log-plan-context')
  const selectedDate = $('#log-form').elements.training_date.value
  if (!selectedDate) {
    target.textContent = '选择日期后查看对应的周计划安排。'
    return
  }
  target.textContent = '正在读取这一天的计划安排…'
  try {
    const result = await api('/api/plan/session?training_date=' + encodeURIComponent(selectedDate))
    if (result.status === 'training' && result.session) {
      target.textContent = '对应计划训练：' + result.session.title + '。保存后会关联到这一天的计划。'
    } else if (result.status === 'rest') {
      target.textContent = '这一天是计划休息日；如果有额外训练，也可以照常记录。'
    } else if (result.status === 'before_registration') {
      target.textContent = '日期早于账号注册日，不能记录。'
    } else {
      target.textContent = '这一天没有可关联的周计划；保存的训练记录仍会正常保留。'
    }
  } catch (error) {
    target.textContent = error.message || '暂时无法读取这一天的计划安排。'
  }
}
refreshLogPlanContext()
$('#log-form').elements.training_date.addEventListener('change', refreshLogPlanContext)
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
    const result = await api('/api/log', { method: 'POST', body: JSON.stringify(payload) })
    form.reset()
    $('#log-form').training_date.value = localDateString()
    refreshLogPlanContext()
    $('#skip-reason-wrap').classList.add('hidden')
    notify(result.message || '训练记录已保存。')
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
    target.innerHTML = result.items.map((item) => {
      const effortText = item.rpe ? 'RPE ' + escapeHtml(item.rpe) : '未填 RPE'
      const skipText = item.skip_reason ? ' · ' + escapeHtml(reasonLabels[item.skip_reason]) : ''
      const plannedText = item.planned_session_title ? '<p>关联计划：' + escapeHtml(item.planned_session_title) + '</p>' : ''
      const noteText = item.note ? '<p>' + escapeHtml(item.note) + '</p>' : ''
      return '<article class="log-entry"><div><b>' + escapeHtml(item.training_date) + ' · ' + escapeHtml(completionLabels[item.completion]) + '</b><p>' + effortText + skipText + '</p>' + plannedText + noteText + '</div><span class="log-dot ' + escapeHtml(item.completion) + '"></span></article>'
    }).join('')
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
// 日期变化时刷新今日状态，由服务端返回新一天需要的确认状态。
function expireScreeningForNewDay() {
  if (!screeningDate || screeningDate === localDateString()) return
  screeningDate = null
  safetyStatus = 'ask'
  updateSafetyUi()
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
    const guidance = $('#review-guidance')
    const plannedRecorded = summary.planned_elapsed_day_count - summary.planned_unlogged_count
    let guidanceText
    if (!summary.planned_day_count) {
      guidanceText = '这周没有可对照的已保存周计划。生成周计划并记录训练后，周回顾会展示执行情况。'
    } else if (!summary.planned_elapsed_day_count) {
      guidanceText = '本周计划尚未开始，或计划训练日还未到。等训练日经过并记录情况后，再参考本周数据调整。'
    } else if (!plannedRecorded) {
      guidanceText = '本周已到的计划训练日目前都还没有对应记录。先记录实际完成情况，再决定是否调整下周安排。'
    } else if (summary.planned_skipped_count > summary.planned_completed_count + summary.planned_partial_count) {
      guidanceText = '本周未进行的计划日多于完成或部分完成的计划日。下周可考虑减少训练日或缩短单次时长；也可以结合实际原因自行决定。'
    } else if (summary.average_rpe != null && summary.average_rpe >= 8) {
      guidanceText = '本周平均主观用力程度为 ' + summary.average_rpe + ' / 10。下周可考虑维持或减少训练天数、单次时长，按恢复感受自行调整。'
    } else if (summary.planned_unlogged_count > 0) {
      guidanceText = '截至今天，已到的计划训练日：完成 ' + summary.planned_completed_count + ' 天、部分完成 ' + summary.planned_partial_count + ' 天、未进行 ' + summary.planned_skipped_count + ' 天、未记录 ' + summary.planned_unlogged_count + ' 天。补充记录能让下周回顾更准确。'
    } else {
      guidanceText = '截至今天已到的计划训练日都有记录。可以结合完成情况和用力感保持或微调下周安排；系统不会自动增加训练量。'
    }
    guidance.innerHTML = '<b>下周调整参考</b><p>' + escapeHtml(guidanceText) + '</p>'
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
      const planText = day.before_registration ? '注册前：不适用' : day.planned_session_title
        ? '计划训练：' + escapeHtml(day.planned_session_title)
        : day.plan_status === 'training' ? '计划训练安排暂不可用'
        : day.plan_status === 'rest' ? '计划休息日'
        : day.plan_status === 'legacy_plan' ? '旧计划未记录具体训练日' : '无周计划'
      return '<article class="panel review-day"><div class="review-day-head"><b>' + weekdayLabels[index] + ' · ' + escapeHtml(day.date) + '</b><span class="review-planned-label">' + planText + '</span></div><p class="review-signal">' + stateText + '</p><div class="review-log-list">' + logHtml + '</div></article>'
    }).join('')
  } catch (error) {
    if (await handleSafetyGateError(error)) return
    stats.innerHTML = ''
    $('#review-guidance').innerHTML = '<b>下周调整参考</b><p>暂时无法读取训练计划和记录，请稍后重试。</p>'
    daysTarget.innerHTML = `<article class="panel review-error">${escapeHtml(error.message)}</article>`
  }
}

// 根据 loading / ask / clear / stop 状态，只显示对应的筛查或暂停界面。
function updateSafetyUi() {
  const loading = safetyStatus === 'loading'
  const cleared = safetyStatus === 'clear'
  const held = safetyStatus === 'stop'
  const module = $('#safety-check-module')
  module.classList.toggle('is-clear', cleared)
  module.classList.toggle('is-stop', held)
  $('#safety-module-loading').classList.toggle('hidden', !loading)
  $('#safety-module-actions').classList.toggle('hidden', loading || cleared || held)
  $('#safety-module-done').classList.toggle('hidden', loading || (!cleared && !held))
  $('#safety-module-title').textContent = held
    ? '今天先暂停训练'
    : cleared ? '今天已确认身体没有明显不适' : '训练前确认一下身体感受'
  $('#safety-module-message').textContent = held
    ? '今天不显示训练安排。若出现紧急或严重症状，请及时联系医疗服务。'
    : cleared ? '今天的训练安排已开放；如果身体状况变化，请重新确认。'
      : '如果今天有明显不适或无法判断，请暂停今天的训练建议。'
  $('#safety-module-status').textContent = held ? '今日训练建议已暂停' : '今日确认已完成'
  $('#safety-recheck').classList.toggle('hidden', !cleared)
}

async function submitSafetyChoice(noSymptoms) {
  if (safetyStatus === 'stop') return
  const buttons = [$('#safety-no-symptoms'), $('#safety-symptoms')]
  buttons.forEach((button) => { button.disabled = true })
  try {
    const result = await api('/api/safety-check', {
      method: 'POST',
      body: JSON.stringify({
        completed: true,
        no_symptoms: noSymptoms,
        symptoms: noSymptoms ? [] : ['uncertain'],
      }),
    })
    safetyStatus = result.status
    screeningDate = result.screening_date || null
    updateSafetyUi()
    await refreshToday()
  } catch (error) {
    notify(error.message, 'error')
  } finally {
    buttons.forEach((button) => { button.disabled = false })
  }
}
$('#safety-no-symptoms').addEventListener('click', () => submitSafetyChoice(true))
$('#safety-symptoms').addEventListener('click', () => submitSafetyChoice(false))
$('#safety-recheck').addEventListener('click', async () => {
  if (safetyStatus !== 'clear') return
  safetyStatus = 'ask'
  screeningDate = null
  updateSafetyUi()
  try {
    await api('/api/safety-check', {
      method: 'POST',
      body: JSON.stringify({ completed: false, no_symptoms: false, symptoms: [] }),
    })
    await refreshToday()
  } catch (error) {
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
  renderAccountAvatar(user.id)
  document.body.classList.remove('auth-open')
  $('#auth-gate').classList.add('hidden')
  $('#open-profile-button').classList.remove('hidden')
  $('#account-dialog-title').textContent = user.display_name
  $('#account-dialog-username').textContent = '账号：' + user.username
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
function closeAccountDialog() {
  $('#account-dialog').close()
  $('#open-profile-button').setAttribute('aria-expanded', 'false')
}
function renderAccountBodyInsights(profile, weightHistory) {
  const module = $('#account-body-insights')
  const history = [...(weightHistory || [])].slice(0, 12).reverse()
  const weight = Number(profile.weight_kg)
  const heightM = Number(profile.height_cm) / 100
  const isAdult = profile.age_band !== 'under_18'
  const bmi = isAdult && heightM > 0 ? weight / (heightM * heightM) : null
  $('#account-bmi-value').textContent = bmi == null ? '不适用' : bmi.toFixed(1)
  $('#account-bmi-label').textContent = bmi == null ? '未成年人不使用成人参考值' : '成人参考值，不作诊断'
  $('#account-weight-value').textContent = weight.toFixed(1)
  const targetWeight = profile.target_weight_kg == null ? null : Number(profile.target_weight_kg)
  $('#account-weight-target').textContent = targetWeight == null ? '尚未设置' : targetWeight.toFixed(1) + ' kg'
  $('#account-weight-target-progress').textContent = targetWeight == null
    ? '由你自己设定的参考目标'
    : Math.abs(targetWeight - weight) < 0.05
      ? '已达到你设定的目标'
      : '距离目标 ' + Math.abs(targetWeight - weight).toFixed(1) + ' kg'
  $('#edit-weight-target').textContent = targetWeight == null ? '设置目标' : '修改目标'
  const delta = history.length > 1 ? Number(history[history.length - 1].weight_kg) - Number(history[history.length - 2].weight_kg) : null
  $('#account-weight-delta').textContent = delta == null ? '暂无' : (delta > 0 ? '+' : '') + delta.toFixed(1)
  if (!history.length) {
    $('#account-weight-chart').innerHTML = '<p class="body-chart-empty">还没有体重记录，记录今天体重后会显示趋势。</p>'
  } else {
    const values = history.map((item) => Number(item.weight_kg))
    const minValue = Math.min(...values)
    const maxValue = Math.max(...values)
    const padding = Math.max((maxValue - minValue) * 0.25, 0.4)
    const low = minValue - padding
    const range = maxValue - minValue + padding * 2
    const points = values.map((value, index) => {
      const x = history.length === 1 ? 150 : 12 + index * (276 / (history.length - 1))
      const y = 66 - ((value - low) / range) * 52
      return { x, y }
    })
    const pointList = points.map((point) => point.x + ',' + point.y).join(' ')
    const circles = points.map((point) => '<circle cx="' + point.x + '" cy="' + point.y + '" r="3.5"></circle>').join('')
    const firstDate = escapeHtml(history[0].date)
    const lastDate = escapeHtml(history[history.length - 1].date)
    $('#account-weight-chart').innerHTML = '<svg viewBox="0 0 300 82" preserveAspectRatio="none" aria-hidden="true"><line x1="10" y1="66" x2="290" y2="66"></line><polyline points="' + pointList + '"></polyline>' + circles + '</svg><div class="body-chart-dates"><span>' + firstDate + '</span><span>' + lastDate + '</span></div>'
  }
  $('#quick-weight-form').elements.weight_kg.value = weight.toFixed(1)
  module.classList.remove('hidden')
}

async function openAccountDialog() {
  $('#account-dialog').showModal()
  $('#open-profile-button').setAttribute('aria-expanded', 'true')
  $('#close-account-dialog').focus()
  const summary = $('#account-dialog-profile-summary')
  const insights = $('#account-body-insights')
  const goal = $('#account-training-goal')
  insights.classList.add('hidden')
  summary.textContent = '正在读取身体档案…'
  goal.textContent = '正在读取…'
  try {
    const result = await api('/api/body-profile')
    const profile = result.profile
    if (!profile) {
      summary.textContent = '尚未填写身体档案'
      $('#account-weight-chart').innerHTML = '<p class="body-chart-empty">填写身高和体重后，这里会显示 BMI 参考值和体重趋势。</p>'
      goal.textContent = '填写身体档案后可生成计划'
      return
    }
    const age = AGE_BAND_LABELS[profile.age_band] || '未记录年龄段'
    const details = [age, '身高 ' + profile.height_cm + ' 厘米', '体重 ' + profile.weight_kg + ' 千克']
    if (profile.body_fat_percent != null) details.push('体脂率 ' + profile.body_fat_percent + '%')
    if (profile.waist_cm != null) details.push('腰围 ' + profile.waist_cm + ' 厘米')
    if (profile.target_weight_kg != null) details.push('自设目标 ' + profile.target_weight_kg + ' 千克')
    summary.textContent = details.join(' · ')
    renderAccountBodyInsights(profile, result.weight_history || [])
  } catch (error) {
    summary.textContent = error.message || '身体档案暂时无法读取。'
    return
  }
  try {
    const result = await api('/api/plan/preferences')
    const goalLabels = { fitness: '综合体能', strength: '力量基础', fat_loss: '增加日常活动' }
    goal.textContent = goalLabels[result.preferences.goal] || '尚未设置'
  } catch {
    goal.textContent = '尚未生成训练计划'
  }
}

$('#quick-weight-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const form = event.currentTarget
  const button = form.querySelector('button[type="submit"]')
  button.disabled = true
  try {
    const weightKg = Number(new FormData(form).get('weight_kg'))
    await api('/api/body-weight', { method: 'POST', body: JSON.stringify({ weight_kg: weightKg }) })
    planRecommendationsLoaded = false
    const result = await api('/api/body-profile')
    if (result.profile) {
      const profile = result.profile
      const details = [AGE_BAND_LABELS[profile.age_band] || '未记录年龄段', '身高 ' + profile.height_cm + ' 厘米', '体重 ' + profile.weight_kg + ' 千克']
      if (profile.body_fat_percent != null) details.push('体脂率 ' + profile.body_fat_percent + '%')
      if (profile.waist_cm != null) details.push('腰围 ' + profile.waist_cm + ' 厘米')
      if (profile.target_weight_kg != null) details.push('自设目标 ' + profile.target_weight_kg + ' 千克')
      $('#account-dialog-profile-summary').textContent = details.join(' · ')
      renderAccountBodyInsights(profile, result.weight_history || [])
    }
    await loadBodyProfile()
    if ($('#page-plan').classList.contains('active')) loadPlanRecommendations()
    notify('今日体重已记录。')
  } catch (error) {
    notify(error.message, 'error')
  } finally {
    button.disabled = false
  }
})
$('#edit-weight-target').addEventListener('click', async () => {
  closeAccountDialog()
  if (await loadBodyProfile()) openBodyProfileModal()
})
$('#account-goal-button').addEventListener('click', () => {
  closeAccountDialog()
  showPage('plan')
})
$('#open-profile-button').addEventListener('click', openAccountDialog)
$('#close-account-dialog').addEventListener('click', closeAccountDialog)
$('#account-dialog').addEventListener('click', (event) => { if (event.target === $('#account-dialog')) closeAccountDialog() })
$('#account-dialog').addEventListener('close', () => $('#open-profile-button').setAttribute('aria-expanded', 'false'))
$('#view-profile-button').addEventListener('click', async () => {
  closeAccountDialog()
  if (await loadBodyProfile()) openBodyProfileModal()
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


// 头像按本机账号分别保存在浏览器中；裁剪在本地完成，原图不会上传。
let avatarObjectUrl = null
let avatarCropBounds = null
let avatarDragState = null

function avatarStorageKey(userId) {
  return `fitnessCoachAvatar:${userId}`
}

function paintAvatar(element, dataUrl, fallback = '禾') {
  if (!element) return
  element.replaceChildren()
  if (!dataUrl) {
    element.textContent = fallback
    element.classList.remove('has-avatar-image')
    return
  }
  const image = document.createElement('img')
  image.src = dataUrl
  image.alt = ''
  element.append(image)
  element.classList.add('has-avatar-image')
}

function renderAccountAvatar(userId) {
  let dataUrl = null
  try { dataUrl = localStorage.getItem(avatarStorageKey(userId)) } catch { /* 浏览器禁用本地存储时显示默认头像 */ }
  paintAvatar($('#user-menu-avatar'), dataUrl)
  paintAvatar($('#account-dialog-avatar'), dataUrl)
}

function cropImageRect() {
  const viewport = $('#avatar-crop-viewport').getBoundingClientRect()
  const image = $('#avatar-crop-image').getBoundingClientRect()
  return { viewport, image, left: image.left - viewport.left, top: image.top - viewport.top }
}

function setAvatarCropFrame(size, left, top) {
  if (!avatarCropBounds) return
  const side = Math.max(24, Math.min(size, avatarCropBounds.maxSide))
  const maxLeft = avatarCropBounds.left + avatarCropBounds.width - side
  const maxTop = avatarCropBounds.top + avatarCropBounds.height - side
  const x = Math.max(avatarCropBounds.left, Math.min(left, maxLeft))
  const y = Math.max(avatarCropBounds.top, Math.min(top, maxTop))
  const frame = $('#avatar-crop-selection')
  frame.style.width = `${side}px`
  frame.style.height = `${side}px`
  frame.style.left = `${x}px`
  frame.style.top = `${y}px`
}

function initializeAvatarCrop() {
  const { image, left, top } = cropImageRect()
  const width = image.width
  const height = image.height
  const maxSide = Math.min(width, height)
  if (!maxSide) return
  avatarCropBounds = { left, top, width, height, maxSide }
  const size = maxSide * Number($('#avatar-crop-size').value) / 100
  setAvatarCropFrame(size, left + (width - size) / 2, top + (height - size) / 2)
}

function closeAvatarCrop() {
  const dialog = $('#avatar-crop-dialog')
  if (dialog.open) dialog.close()
  if (avatarObjectUrl) URL.revokeObjectURL(avatarObjectUrl)
  avatarObjectUrl = null
  avatarCropBounds = null
  avatarDragState = null
  $('#avatar-file-input').value = ''
}

$('#change-avatar-button').addEventListener('click', () => $('#avatar-file-input').click())
$('#avatar-file-input').addEventListener('change', (event) => {
  const file = event.currentTarget.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    notify('请选择图片文件。', 'error')
    event.currentTarget.value = ''
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    notify('图片不能超过 10 MB，请先压缩后再选择。', 'error')
    event.currentTarget.value = ''
    return
  }
  if (avatarObjectUrl) URL.revokeObjectURL(avatarObjectUrl)
  avatarObjectUrl = URL.createObjectURL(file)
  const image = $('#avatar-crop-image')
  image.onload = () => {
    $('#avatar-crop-size').value = '68'
    $('#avatar-crop-size-label').textContent = '68%'
    $('#avatar-crop-dialog').showModal()
    requestAnimationFrame(initializeAvatarCrop)
  }
  image.onerror = () => {
    notify('图片读取失败，请换一张图片试试。', 'error')
    closeAvatarCrop()
  }
  image.src = avatarObjectUrl
})

$('#avatar-crop-size').addEventListener('input', (event) => {
  const percent = Number(event.currentTarget.value)
  $('#avatar-crop-size-label').textContent = `${percent}%`
  if (!avatarCropBounds) return
  const frame = $('#avatar-crop-selection')
  const oldSide = frame.getBoundingClientRect().width
  const centerX = Number.parseFloat(frame.style.left) + oldSide / 2
  const centerY = Number.parseFloat(frame.style.top) + oldSide / 2
  const newSide = avatarCropBounds.maxSide * percent / 100
  setAvatarCropFrame(newSide, centerX - newSide / 2, centerY - newSide / 2)
})

$('#avatar-crop-selection').addEventListener('pointerdown', (event) => {
  if (!avatarCropBounds) return
  const frame = event.currentTarget
  const rect = frame.getBoundingClientRect()
  avatarDragState = { pointerId: event.pointerId, startX: event.clientX, startY: event.clientY, left: Number.parseFloat(frame.style.left), top: Number.parseFloat(frame.style.top) }
  frame.setPointerCapture(event.pointerId)
  event.preventDefault()
})
$('#avatar-crop-selection').addEventListener('pointermove', (event) => {
  if (!avatarDragState || avatarDragState.pointerId !== event.pointerId) return
  setAvatarCropFrame(Number.parseFloat(event.currentTarget.style.width), avatarDragState.left + event.clientX - avatarDragState.startX, avatarDragState.top + event.clientY - avatarDragState.startY)
})
$('#avatar-crop-selection').addEventListener('pointerup', () => { avatarDragState = null })
$('#avatar-crop-selection').addEventListener('pointercancel', () => { avatarDragState = null })

$('#save-avatar-crop').addEventListener('click', () => {
  if (!activeAccount || !avatarCropBounds) return
  const imageElement = $('#avatar-crop-image')
  const imageRect = imageElement.getBoundingClientRect()
  const frame = $('#avatar-crop-selection').getBoundingClientRect()
  const scaleX = imageElement.naturalWidth / imageRect.width
  const scaleY = imageElement.naturalHeight / imageRect.height
  const sourceX = Math.max(0, (frame.left - imageRect.left) * scaleX)
  const sourceY = Math.max(0, (frame.top - imageRect.top) * scaleY)
  const sourceSize = Math.min(frame.width * scaleX, frame.height * scaleY, imageElement.naturalWidth - sourceX, imageElement.naturalHeight - sourceY)
  const canvas = document.createElement('canvas')
  canvas.width = 320
  canvas.height = 320
  const context = canvas.getContext('2d')
  context.drawImage(imageElement, sourceX, sourceY, sourceSize, sourceSize, 0, 0, canvas.width, canvas.height)
  const dataUrl = canvas.toDataURL('image/jpeg', 0.88)
  try {
    localStorage.setItem(avatarStorageKey(activeAccount.id), dataUrl)
    paintAvatar($('#user-menu-avatar'), dataUrl)
    paintAvatar($('#account-dialog-avatar'), dataUrl)
    closeAvatarCrop()
    notify('头像已更新。', 'success')
  } catch {
    notify('头像保存失败，请换一张较小的图片后重试。', 'error')
  }
})

$('#close-avatar-crop').addEventListener('click', closeAvatarCrop)
$('#cancel-avatar-crop').addEventListener('click', closeAvatarCrop)
$('#avatar-crop-dialog').addEventListener('click', (event) => { if (event.target === $('#avatar-crop-dialog')) closeAvatarCrop() })
$('#avatar-crop-dialog').addEventListener('close', () => {
  if (avatarObjectUrl) URL.revokeObjectURL(avatarObjectUrl)
  avatarObjectUrl = null
  avatarCropBounds = null
  avatarDragState = null
  $('#avatar-file-input').value = ''
})

updateSafetyUi()
checkAuthentication()
