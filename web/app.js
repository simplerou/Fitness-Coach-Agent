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
let weeklyPlanSuggestion = null

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
  if (name === 'diet') refreshDietPage()
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
    await loadDietTargets()
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
    const dataContext = '本周饮食记录 ' + summary.diet_meal_count + ' 餐、' + summary.diet_days_with_meals + ' 天；体重记录 ' + summary.weight_days_logged + ' 天。它们用于回顾生活状态，不会单独推断训练强度或营养目标。'
    let nextAction = null
    if (summary.planned_day_count && plannedRecorded > 0 && summary.planned_skipped_count > summary.planned_completed_count + summary.planned_partial_count) {
      nextAction = { type: 'reduce_load', reason: 'skipped' }
    } else if (summary.planned_day_count && plannedRecorded > 0 && summary.average_rpe != null && summary.average_rpe >= 8) {
      nextAction = { type: 'reduce_load', reason: 'high_rpe' }
    }
    weeklyPlanSuggestion = nextAction
    const actionHtml = nextAction
      ? '<button class="button button-primary review-apply" type="button" id="apply-review-plan-suggestion">将建议带入计划设置</button><span class="review-apply-note">带入后可检查或修改，再手动生成计划。</span>'
      : ''
    guidance.innerHTML = '<b>下周调整参考</b><p>' + escapeHtml(guidanceText) + '</p><p class="review-data-context">' + escapeHtml(dataContext) + '</p>' + actionHtml
    const statItems = [
      ['日志条数', `${summary.session_count} 条`],
      ['按计划完成', `${summary.completed_count} 次`],
      ['部分完成', `${summary.partial_count} 次`],
      ['未进行', `${summary.skipped_count} 次`],
      ['平均 RPE', summary.average_rpe == null ? `未记录（${summary.rpe_count} 条）` : `${summary.average_rpe} / 10（${summary.rpe_count} 条）`],
      ['饮食记录', `${summary.diet_meal_count} 餐 · ${summary.diet_days_with_meals} 天`],
      ['饮水记录', summary.diet_water_total_ml == null ? '未记录' : `${summary.diet_water_total_ml} 毫升 · ${summary.diet_water_days_logged} 天`],
      ['饮食完整日', `${summary.diet_days_marked_complete} 天`],
      ['体重记录', `${summary.weight_days_logged} 天`],
    ]
    stats.innerHTML = statItems.map(([label, value]) => `<article class="panel review-stat"><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b></article>`).join('')
    $('#apply-review-plan-suggestion')?.addEventListener('click', async () => {
      if (!weeklyPlanSuggestion) return
      await loadPlanPreferences()
      const form = $('#plan-form')
      const shortenSession = () => {
        const current = Number(form.elements.session_minutes.value)
        const shorter = ({ 60: 45, 45: 30, 30: 20 })[current]
        if (shorter) form.elements.session_minutes.value = String(shorter)
        return Boolean(shorter)
      }
      const reduceTrainingDays = () => {
        const weekdays = selectedTrainingWeekdays()
        if (weekdays.length <= 1) return false
        const retained = weekdays.slice(0, -1)
        $$('input[name="training_weekdays"]').forEach((input) => {
          input.checked = retained.includes(Number(input.value))
        })
        updateWeekdayCount()
        return true
      }
      const changed = weeklyPlanSuggestion.reason === 'skipped'
        ? (reduceTrainingDays() || shortenSession())
        : (shortenSession() || reduceTrainingDays())
      if (!changed) {
        notify('当前训练时长和训练日数已处于可选下限，建议先保持安排，并结合恢复情况再决定。')
        return
      }
      planFormEdited = true
      showPage('plan')
      notify('已把本周回顾建议带入计划设置。检查训练日和时长后，再手动生成下周计划。')
    })
    daysTarget.innerHTML = result.days.map((day, index) => {
      const signal = day.signal
      const stateText = day.before_registration ? '注册前：不适用' : signal
        ? `${escapeHtml(readinessLabels[signal.readiness] || '未知')} · 睡眠 ${signal.sleep_hours == null ? '未记录' : `${escapeHtml(signal.sleep_hours)} 小时`} · 静息心率 ${signal.resting_hr == null ? '未记录' : `${escapeHtml(signal.resting_hr)} 次/分`}`
        : '状态：未记录'
      const logHtml = day.before_registration ? '<div class="review-missing">注册前：不适用</div>' : day.logs.length
        ? day.logs.map((log) => `<div class="review-log"><b>${escapeHtml(completionLabels[log.completion] || '未知记录')}</b><span>${log.rpe == null ? 'RPE 未记录' : `RPE ${escapeHtml(log.rpe)}`}${log.skip_reason ? ` · ${escapeHtml(reasonLabels[log.skip_reason] || '')}` : ''}</span>${log.note ? `<p>${escapeHtml(log.note)}</p>` : ''}</div>`).join('')
        : '<div class="review-missing">训练日志：未记录</div>'
      const diet = day.diet || {}
      const calorieText = diet.calories_kcal == null ? '热量未记录' : `热量 ${diet.calories_kcal} 千卡（${diet.calories_logged_count}/${diet.meal_count} 餐填写）`
      const macroParts = [
        diet.protein_g == null ? '' : `蛋白质 ${diet.protein_g}g`,
        diet.carbs_g == null ? '' : `碳水 ${diet.carbs_g}g`,
        diet.fat_g == null ? '' : `脂肪 ${diet.fat_g}g`,
      ].filter(Boolean)
      const macroText = macroParts.length ? macroParts.join(' · ') : '营养素未记录'
      const mealText = diet.meals?.length ? diet.meals.map((meal) => `${escapeHtml(DIET_MEAL_LABELS[meal.meal_type] || '餐食')}：${escapeHtml(meal.description)}`).join(' · ') : '餐食未记录'
      const waterText = diet.water_ml == null ? '饮水未记录' : `饮水 ${diet.water_ml} 毫升`
      const completeText = diet.complete == null ? '完整度未标记' : diet.complete ? '已标记饮食记录完整' : '饮食记录尚未标记完整'
      const weightText = day.weight_kg == null ? '体重未记录' : `体重 ${day.weight_kg} 千克`
      const dietHtml = day.before_registration ? '<div class="review-diet-summary">饮食、饮水与体重：注册前不适用</div>' : `<div class="review-diet-summary"><b>饮食与身体记录</b><span>${mealText}</span><span>${calorieText} · ${macroText}</span><span>${waterText} · ${completeText} · ${weightText}</span></div>`
      const planText = day.before_registration ? '注册前：不适用' : day.planned_session_title
        ? '计划训练：' + escapeHtml(day.planned_session_title)
        : day.plan_status === 'training' ? '计划训练安排暂不可用'
        : day.plan_status === 'rest' ? '计划休息日'
        : day.plan_status === 'legacy_plan' ? '旧计划未记录具体训练日' : '无周计划'
      return '<article class="panel review-day"><div class="review-day-head"><b>' + weekdayLabels[index] + ' · ' + escapeHtml(day.date) + '</b><span class="review-planned-label">' + planText + '</span></div><p class="review-signal">' + stateText + '</p><div class="review-log-list">' + logHtml + '</div>' + dietHtml + '</article>'
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

function clearAuthError() { $('#auth-error').textContent = '' }
function setUsernameError(message) {
  const field = $('#auth-form').elements.username, node = $('#auth-username-error')
  node.textContent = message; node.classList.toggle('hidden', !message)
  field.classList.toggle('input-error', Boolean(message)); field.setAttribute('aria-invalid', String(Boolean(message)))
}
function setConfirmPasswordError(message) {
  const field = $('#auth-form').elements.password_confirm, node = $('#password-confirm-error')
  node.textContent = message; node.classList.toggle('hidden', !message)
  field.classList.toggle('input-error', Boolean(message)); field.setAttribute('aria-invalid', String(Boolean(message)))
}
function validateConfirmPassword(allowEmpty = false) {
  const form = $('#auth-form'), password = form.elements.password.value.trim(), confirm = form.elements.password_confirm.value.trim()
  if (!confirm) { setConfirmPasswordError(allowEmpty ? '请再次输入密码。' : ''); return !allowEmpty }
  if (password !== confirm) { setConfirmPasswordError('两次输入的密码不一致，请重新确认。'); return false }
  setConfirmPasswordError(''); return true
}
function authFailureMessage(error) {
  if (error.status === 401) return '账号或密码不正确，请检查后重试。'
  if (error.status === 429) return '尝试次数过多，请稍后再试。'
  if (error.status === 403 || error.status === 423) return '账号当前暂不可用，请稍后重试或联系管理员。'
  if (error.status === 409) return error.message
  if (error.status === 422) return '输入内容不符合要求，请检查后重试。'
  if (!error.status || error.status >= 500) return '网络或服务暂时异常，请稍后重试。'
  return error.message || '暂时无法完成请求，请稍后重试。'
}
function setAuthLoading(loading) {
  const button = $('#auth-submit'); button.disabled = loading
  button.classList.toggle('is-loading', loading); button.setAttribute('aria-busy', String(loading))
  button.textContent = loading ? (authMode === 'register' ? '正在注册…' : '正在登录…') : (authMode === 'register' ? '注册并进入' : '登录')
}
let authMode = "login"

function setAuthMode(mode) {
  const modeChanged = authMode !== mode
  authMode = mode
  const register = mode === "register"
  if (modeChanged) {
    $('#auth-form').reset()
    $$('[data-password-toggle]').forEach((button) => {
      const field = $('#auth-form').elements[button.dataset.passwordToggle]
      field.type = 'password'
      button.innerHTML = passwordEyeIcon(false)
      button.setAttribute('aria-label', '显示密码')
      button.setAttribute('title', '显示密码')
      button.setAttribute('aria-pressed', 'false')
    })
  }

  $('#auth-switch-login').classList.toggle('hidden', register)
  $('#auth-switch-register').classList.toggle('hidden', !register)

  $('#display-name-field').classList.toggle('hidden', !register)
  $('#password-confirm-field').classList.toggle('hidden', !register)
  $('#auth-form').elements.password_confirm.required = register
  $('#auth-form').elements.password.autocomplete = register ? 'new-password' : 'current-password'
  $('#auth-title').textContent = register ? '创建你的训练账号' : '欢迎回来'
  $('#auth-description').textContent = register ? '注册后会为你单独保存档案、训练计划和记录。' : '登录后查看你自己的身体档案、训练计划和记录。'
  $('#auth-submit').textContent = register ? '注册并进入' : '登录'
  clearAuthError()
  setUsernameError('')
  setConfirmPasswordError('')
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
  const form = event.currentTarget, username = form.elements.username.value.trim(), password = form.elements.password.value, confirm = form.elements.password_confirm.value
  clearAuthError()
  if (!username) { setUsernameError('请填写用户名。'); form.elements.username.focus(); return }
  if (!password || (authMode === 'register' && !password.trim())) { $('#auth-error').textContent = '请填写密码。'; form.elements.password.focus(); return }
  if (authMode === 'register' && !confirm.trim()) {
    setConfirmPasswordError('请再次输入密码。'); $('#auth-error').textContent = '请再次输入密码后继续注册。'; form.elements.password_confirm.focus(); return
  }
  if (authMode === 'register' && !validateConfirmPassword(true)) {
    $('#auth-error').textContent = '两次输入的密码不一致，请重新确认。'; form.elements.password_confirm.focus(); return
  }
  if (authMode === 'register' && password.length < 8) { $('#auth-error').textContent = '注册密码至少需要 8 位。'; form.elements.password.focus(); return }
  const payload = { username, password }
  if (authMode === 'register' && form.elements.display_name.value.trim()) payload.display_name = form.elements.display_name.value.trim()
  setAuthLoading(true)
  try {
    const result = await api(authMode === 'register' ? '/api/auth/register' : '/api/auth/login', { method: 'POST', body: JSON.stringify(payload) })
    revealAccount(result.user); broadcastAuthChange(); await startAuthenticatedApplication()
  } catch (error) { $('#auth-error').textContent = authFailureMessage(error) }
  finally { setAuthLoading(false) }
})
const authForm = $('#auth-form')
for (const name of ['username', 'password', 'password_confirm']) {
  authForm.elements[name].addEventListener('input', () => {
    clearAuthError()
    if (name === 'username') setUsernameError('')
    if (name === 'password' || name === 'password_confirm') {
      const hasConfirmError = !$('#password-confirm-error').classList.contains('hidden')
      if (hasConfirmError) validateConfirmPassword()
      else if (name === 'password') authForm.elements.password.classList.remove('input-error')
    }
  })
}
authForm.elements.password_confirm.addEventListener('blur', () => {
  if (authMode === 'register' && authForm.elements.password.value.trim()) validateConfirmPassword(true)
})
function passwordEyeIcon(visible) {
  return visible
    ? '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>'
    : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 3 18 18M10.6 10.6a2 2 0 0 0 2.8 2.8M9.9 5.2A10.7 10.7 0 0 1 12 5c6.4 0 10 7 10 7a17 17 0 0 1-3.1 3.9M6.2 6.2C3.5 8 2 12 2 12s3.6 7 10 7c1.4 0 2.6-.3 3.7-.8"/></svg>'
}
$$('[data-password-toggle]').forEach((button) => {
  const field = authForm.elements[button.dataset.passwordToggle]
  button.innerHTML = passwordEyeIcon(false)
  button.addEventListener('click', () => {
    const start = field.selectionStart, end = field.selectionEnd, visible = field.type === 'password'
    field.type = visible ? 'text' : 'password'
    if (start !== null && end !== null) field.setSelectionRange(start, end)
    button.innerHTML = passwordEyeIcon(visible); button.setAttribute('aria-label', visible ? '隐藏密码' : '显示密码')
    button.setAttribute('title', visible ? '隐藏密码' : '显示密码'); button.setAttribute('aria-pressed', String(visible))
  })
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
    await loadDietTargets()
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



// 饮食档案、餐食和规划结果通过当前登录账号读写。
const DIET_MEAL_LABELS = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '加餐' }
let dietLogData = null
let dietTargetInfo = null
let editingDietMealId = null
let dietSearchResults = []
let dietSearchKeyword = ''
let selectedDietFoods = []

function dietSelectedDate() { return $('#diet-date').value || new Date().toISOString().slice(0, 10) }
function dietNumber(value, digits = 0) { return value == null || value === '' ? '未记录' : Number(value).toLocaleString('zh-CN', { maximumFractionDigits: digits }) }
function setDietForm(form, data) {
  for (const [key, value] of Object.entries(data || {})) {
    const field = form.elements.namedItem(key)
    if (!field) continue
    if (field.type === 'checkbox') field.checked = Boolean(value)
    else field.value = value ?? ''
  }
}
function dietFormData(form) {
  const data = Object.fromEntries(new FormData(form).entries())
  for (const field of form.querySelectorAll('input[type=number]')) data[field.name] = field.value.trim() === '' ? null : Number(field.value)
  for (const name of ['calories_kcal', 'protein_g', 'carbs_g', 'fat_g']) {
    data[name] = data[name] == null || String(data[name]).trim() === '' ? null : Number(data[name])
  }
  for (const field of form.querySelectorAll('input[type=checkbox]')) data[field.name] = field.checked
  return data
}
function foodNumber(value) {
  if (value && typeof value === 'object') value = value.value ?? value.amount ?? value.content
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value !== 'string') return null
  const cleaned = value.replace(/,/g, '').match(/-?\d+(?:\.\d+)?/)
  return cleaned ? Number(cleaned[0]) : null
}
function normalizeDietFood(item) {
  const listNutrition = [item.nutrition, item.nutrients, item.nutrition_info, item.nutrition_per_100g].find(Array.isArray) || []
  const listValues = {}
  for (const entry of listNutrition) {
    if (!entry || typeof entry !== 'object') continue
    const label = String(entry.name || entry.nutrient || entry.label || entry.title || '')
    const normalizedLabel = label.toLowerCase()
    const value = entry.value ?? entry.amount ?? entry.content
    if (/protein|蛋白/.test(normalizedLabel)) listValues.protein_g = value
    else if (/carb|碳水/.test(normalizedLabel)) listValues.carbs_g = value
    else if (/fat|脂肪/.test(normalizedLabel)) listValues.fat_g = value
    else if (/energy|calor|能量|热量/.test(normalizedLabel)) listValues.calories_kcal = value
  }
  const sources = [item, item.nutrition, item.nutrients, item.nutrition_info, item.nutrition_per_100g, listValues].filter((value) => value && !Array.isArray(value) && typeof value === 'object')
  const lookup = (aliases) => {
    for (const source of sources) {
      for (const [key, value] of Object.entries(source)) {
        const normalized = key.toLowerCase().replace(/[^a-z0-9]/g, '')
        if (aliases.includes(normalized)) {
          const number = foodNumber(value)
          if (number != null) return number
        }
      }
    }
    return null
  }
  const name = item.name || item.food_name || item.title || item.foodName || item.description || ''
  // 产品当前按薄荷食物营养字段为每 100 克数据处理。
  const basis = '按每 100 克'
  const per100 = true
  const macros = {
    calories_kcal: lookup(['calorieskcal', 'caloriekcal', 'calorykcal', 'energykcal', 'kcal', 'calories', 'calory', 'calorie', 'energy']),
    protein_g: lookup(['proteing', 'protein', 'protein100g', 'proteinper100g']),
    carbs_g: lookup(['carbsg', 'carbs', 'carbohydrateg', 'carbohydrate', 'carbohydrates', 'carbohydrate100g']),
    fat_g: lookup(['fatg', 'fat', 'fat100g', 'fatper100g']),
  }
  return { name: String(name || '未命名食物'), id: item.id ?? item.food_id ?? item.code ?? '', basis, per100, macros }
}
function renderDietFoodResults(items, keyword = '') {
  dietSearchResults = items || []
  const container = $('#diet-food-search-results')
  if (!dietSearchResults.length) {
    container.innerHTML = keyword
      ? `<p class="fine-print">没有找到匹配食物，可以将“${escapeHtml(keyword)}”作为自定义食物记录。</p><button class="button button-quiet" type="button" data-add-custom-food>添加这个食物</button>`
      : '<p class="fine-print">没有找到匹配食物，请换个关键词搜索。</p>'
    return
  }
  container.innerHTML = dietSearchResults.map((raw, index) => {
    const food = normalizeDietFood(raw)
    const summary = Object.values(food.macros).every((value) => value != null)
      ? `${food.macros.calories_kcal} kcal · 蛋白质 ${food.macros.protein_g}g · 碳水 ${food.macros.carbs_g}g · 脂肪 ${food.macros.fat_g}g / 100g`
      : '薄荷食物库暂未提供完整营养字段'
    return `<button class="diet-food-result" type="button" data-diet-food-index="${index}"><strong>${escapeHtml(food.name)}</strong><small>${escapeHtml(summary)}</small></button>`
  }).join('')
}
function updateSelectedDietFoods() {
  const container = $('#diet-selected-foods')
  const summary = $('#diet-nutrition-summary')
  if (selectedDietFoods.length) $('#diet-existing-meal-summary').classList.add('hidden')
  container.innerHTML = selectedDietFoods.map((food, index) => {
    const complete = food.per100 && Object.values(food.macros).every((value) => value != null)
    const note = complete
      ? `本份 ${food.grams}g：${Math.round(food.macros.calories_kcal * food.grams / 100)} kcal · 蛋白质 ${dietNumber(food.macros.protein_g * food.grams / 100, 1)}g · 碳水 ${dietNumber(food.macros.carbs_g * food.grams / 100, 1)}g · 脂肪 ${dietNumber(food.macros.fat_g * food.grams / 100, 1)}g`
      : '自定义食物暂无营养数据'
    return `<div class="diet-selected-food"><div><strong>${escapeHtml(food.name)}</strong><small>${escapeHtml(note)}</small></div><label>克数<input type="number" min="1" max="3000" step="1" value="${food.grams}" data-diet-food-grams="${index}" aria-label="${escapeHtml(food.name)}的克数" /></label><button type="button" class="text-button diet-delete-button" data-remove-diet-food="${index}" aria-label="移除${escapeHtml(food.name)}">移除</button></div>`
  }).join('')
  const description = selectedDietFoods.map((food) => food.name).join('、')
  const portion = selectedDietFoods.map((food) => `${food.name} ${food.grams}g`).join('；')
  const form = $('#diet-meal-form')
  if (selectedDietFoods.length) {
    form.elements.namedItem('description').value = description.slice(0, 500)
    form.elements.namedItem('portion').value = portion.slice(0, 120)
  } else {
    form.elements.namedItem('description').value = ''
    form.elements.namedItem('portion').value = ''
  }
  const complete = selectedDietFoods.length > 0 && selectedDietFoods.every((food) => food.per100 && Object.values(food.macros).every((value) => value != null))
  const totals = { calories_kcal: 0, protein_g: 0, carbs_g: 0, fat_g: 0 }
  if (complete) for (const food of selectedDietFoods) for (const key of Object.keys(totals)) totals[key] += food.macros[key] * food.grams / 100
  for (const key of Object.keys(totals)) form.elements.namedItem(key).value = complete ? String(Math.round(totals[key] * 10) / 10) : ''
  form.elements.namedItem('nutrition_source').value = complete ? 'estimate' : ''
  summary.classList.toggle('hidden', !selectedDietFoods.length)
  summary.innerHTML = selectedDietFoods.length
    ? (complete
      ? `<strong>本餐营养合计</strong><div><span>热量 <b>${Math.round(totals.calories_kcal)} kcal</b></span><span>蛋白质 <b>${dietNumber(totals.protein_g, 1)} g</b></span><span>碳水 <b>${dietNumber(totals.carbs_g, 1)} g</b></span><span>脂肪 <b>${dietNumber(totals.fat_g, 1)} g</b></span></div><small>根据所选克数和薄荷每 100 克数据换算，数值为估算值。</small>`
      : '<strong>本餐营养合计暂不可用</strong><small>请移除没有营养数据的自定义食物后查看自动汇总。</small>')
    : ''
  $('#diet-food-search-status').textContent = selectedDietFoods.length
    ? (complete ? '已按薄荷每 100 克数据和所选克数实时换算。' : '自定义食物没有营养数据，暂不能汇总整餐。')
    : '搜索并选择食物，所选食物会显示在这里。'
}
async function loadDietProfile() {
  const result = await api('/api/diet/profile')
  if (result.profile) setDietForm($('#diet-profile-form'), result.profile)
}
async function loadDietTargets() {
  try {
    dietTargetInfo = await api('/api/diet/targets')
  } catch (error) {
    dietTargetInfo = { status: 'unavailable', message: error.message || '暂时无法读取营养目标。' }
  }
  renderDietDashboard()
}
function renderDietMeals(items) {
  const container = $('#diet-meal-list')
  if (!items.length) { container.innerHTML = '<p>这一天还没有餐食记录。</p>'; return }
  container.innerHTML = `<div class="diet-meal-list">${items.map((item) => {
    const nutrients = [item.calories_kcal != null ? `${dietNumber(item.calories_kcal)} kcal` : '', item.protein_g != null ? `蛋白质 ${dietNumber(item.protein_g, 1)}g` : '', item.carbs_g != null ? `碳水 ${dietNumber(item.carbs_g, 1)}g` : '', item.fat_g != null ? `脂肪 ${dietNumber(item.fat_g, 1)}g` : ''].filter(Boolean).join(' · ')
    return `<article class="diet-meal-item"><div><span class="tag">${escapeHtml(DIET_MEAL_LABELS[item.meal_type] || item.meal_type)}${item.eaten_at ? ` · ${escapeHtml(item.eaten_at)}` : ''}</span><h4>${escapeHtml(item.description)}</h4>${item.portion ? `<p>分量：${escapeHtml(item.portion)}</p>` : ''}<p>${nutrients ? escapeHtml(nutrients) : '未填写营养值'}</p>${item.note ? `<p>${escapeHtml(item.note)}</p>` : ''}</div><div class="diet-meal-actions"><button class="text-button" data-edit-diet-meal="${Number(item.id)}" type="button">编辑</button><button class="text-button diet-delete-button" data-delete-diet-meal="${Number(item.id)}" type="button">删除</button></div></article>`
  }).join('')}</div>`
}
function renderDietDashboard() {
  const items = dietLogData?.items || []
  const plan = dietTargetInfo?.status === 'ready' ? dietTargetInfo : null
  const target = plan?.target || {}
  const sum = (key) => { const rows = items.filter((x) => x[key] != null); return { value: rows.reduce((n,x) => n + Number(x[key]),0), count: rows.length } }
  const cal = sum('calories_kcal'), carbs = sum('carbs_g'), protein = sum('protein_g'), fat = sum('fat_g')
  const set = (id, value) => { document.getElementById(id).textContent = value }
  const show = (x) => x.count ? dietNumber(x.value,1) : '—'
  set('diet-calories-total',show(cal))
  $('#diet-calorie-arc').style.strokeDasharray='0 100'
  const targetNotice = $('#diet-target-notice')
  const targetMessage = $('#diet-target-message')
  const targetBasis = $('#diet-target-basis')
  if (plan) {
    targetNotice.classList.add('hidden')
    targetBasis.textContent = `每日能量参考目标：${dietNumber(target.calories_kcal)} kcal。依据：${plan.summary.goal}；BMR ${dietNumber(plan.summary.bmr_kcal)} kcal（${plan.summary.bmr_source}），TDEE ${dietNumber(plan.summary.tdee_kcal)} kcal（${plan.summary.tdee_source}）。${target.basis} 这是估算起点，实际需要会因个体差异而变化。`
    targetBasis.classList.remove('hidden')
  } else {
    const missing = dietTargetInfo?.missing?.length ? `还需补充：${dietTargetInfo.missing.join('、')}。` : ''
    targetMessage.textContent = `${dietTargetInfo?.message || '正在读取个性化目标…'} ${missing}`.trim()
    targetNotice.classList.remove('hidden')
    targetBasis.classList.add('hidden')
  }
  for(const [key,prefix,targetKey] of [[carbs,'diet-carbs','carbs_g'],[protein,'diet-protein','protein_g'],[fat,'diet-fat','fat_g']]) {
    const g=Number(target[targetKey]),valid=Number.isFinite(g)&&g>0
    set(prefix+'-total',show(key))
    set(prefix+'-target',valid?'/ '+dietNumber(g,1)+' g':'/ 完善档案后显示')
    set(prefix+'-status',key.count?(valid?(key.value>=g?'已达目标':'还差 '+dietNumber(g-key.value,1)+'g'):'已记录 '+dietNumber(key.value,1)+'g'):'未记录')
    document.getElementById(prefix+'-bar').style.width=valid&&key.count?Math.min(100,key.value/g*100)+'%':'0%'
  }
  const energy=[carbs.value*4,protein.value*4,fat.value*9],total=energy.reduce((a,b)=>a+b,0),chart=$('#diet-macro-chart')
  if(total>0&&[carbs,protein,fat].every((item)=>item.count)){const a=energy[0]/total*100,b=a+energy[1]/total*100;chart.style.setProperty('--macro-chart','conic-gradient(#f08a62 0 '+a+'%,#27bf8a '+a+'% '+b+'%,#6188fa '+b+'% 100%)');set('diet-macro-coverage','克数换算')}
  else{chart.style.setProperty('--macro-chart','#edf0ee');set('diet-macro-coverage',total>0?'数据未齐':'暂无数据')}
  set('diet-nutrition-note','仅统计已填写值；碳水 '+carbs.count+'/'+items.length+' 餐、蛋白质 '+protein.count+'/'+items.length+' 餐、脂肪 '+fat.count+'/'+items.length+' 餐有数据。')
  set('diet-insight-title',items.length?'已记录 '+items.length+' 餐，继续补充所选日期饮食':'记录所选日期的饮食，回顾营养结构')
  set('diet-insight-copy',items.length?'统计仅包含已填写的营养数据。':'未填写的营养值不会按零推断。')
  set('diet-insight-action',items.length?'继续添加餐食':'记录第一餐')
}
async function refreshDietLog() {
  const result = await api(`/api/diet?log_date=${encodeURIComponent(dietSelectedDate())}`)
  dietLogData = result
  renderDietMeals(result.items || [])
  renderDietDashboard()
  $('#diet-water-total').innerHTML = `${dietNumber(result.water_ml)} <small>毫升</small>`
  $('#diet-day-complete').checked = Boolean(result.day_complete)
}
function renderDietHistory(items) {
  const container = $('#diet-plan-history')
  if (!items?.length) { container.innerHTML = '<p>还没有保存的饮食规划快照。</p>'; return }
  container.innerHTML = `<div class="diet-history-list">${items.map((item, index) => {
    const plan = item.plan_data || {}
    const created = item.created_at ? new Date(item.created_at).toLocaleString('zh-CN') : item.generated_on
    return `<button type="button" class="diet-history-item" data-diet-history-index="${index}"><strong>${escapeHtml(created)}</strong><span>${escapeHtml(plan.summary?.goal || '饮食规划')} · ${dietNumber(plan.target?.calories_kcal)} kcal/日</span></button>`
  }).join('')}</div>`
  container.querySelectorAll('[data-diet-history-index]').forEach((button) => button.addEventListener('click', () => renderDietPlan(items[Number(button.dataset.dietHistoryIndex)].plan_data)))
}
function renderDietPlan(plan) {
  const container = $('#diet-plan-result')
  if (!plan || plan.status !== 'ready') {
    const fallback = plan?.status === 'professional_support' ? '当前情况需要先咨询医生或注册营养师。' : '请补充所需资料后再生成，不会用猜测值代替。'
    container.className = 'empty-state'
    container.innerHTML = `<p>${escapeHtml(plan?.message || fallback)}</p>${plan?.missing?.length ? `<ul>${plan.missing.map((x) => `<li>${escapeHtml(x)}</li>`).join('')}</ul>` : ''}`
    return
  }
  const s = plan.summary, t = plan.target, records = plan.record_summary || {}
  const weightTrend = Array.isArray(s.weight_trend_14d) ? s.weight_trend_14d : []
  const weightTrendText = weightTrend.length >= 2
    ? '近 14 天有 ' + weightTrend.length + ' 次体重记录，首末记录变化 ' + (Number(s.weight_change_14d) > 0 ? '+' : '') + dietNumber(s.weight_change_14d, 1) + ' kg（仅描述首末记录，不代表趋势或原因）。'
    : weightTrend.length === 1
      ? '近 14 天只有 1 次体重记录，暂时不能判断变化。'
      : '近 14 天没有体重记录，暂时不能判断变化。'
  const weightTargetText = s.target_weight_kg == null
    ? '你尚未设置体重目标；可以留空，系统不会替你设定。'
    : '当前档案体重 ' + dietNumber(s.weight_kg, 1) + ' kg，距你自设目标 ' + dietNumber(Math.abs(Number(s.weight_kg) - Number(s.target_weight_kg)), 1) + ' kg。目标仅用于追踪，不用于推算达成时间。'
  const metric = (label, value, unit = '') => `<div class="diet-metric"><span>${label}</span><strong>${dietNumber(value, 1)}${unit}</strong></div>`
  const list = (items) => items?.length ? `<ul>${items.map((x) => `<li>${escapeHtml(x)}</li>`).join('')}</ul>` : '<p>暂无额外提示。</p>'
  container.className = 'diet-plan-result'
  container.innerHTML = `<section><h4>数据摘要与依据</h4><div class="diet-metrics">${metric('年龄', s.age_years, ' 岁')}${metric('身高', s.height_cm, ' cm')}${metric('体重', s.weight_kg, ' kg')}${metric('BMI（成人参考）', s.bmi)}${metric('BMR', s.bmr_kcal, ' kcal')}${metric('TDEE', s.tdee_kcal, ' kcal')}</div><p>${escapeHtml(s.goal)}；活动水平：${escapeHtml(s.activity_level)}。BMR 来源：${escapeHtml(s.bmr_source)}；TDEE 来源：${escapeHtml(s.tdee_source)}。</p><p>近期完整记录：${dietNumber(records.coverage?.days_marked_complete)} 天。${escapeHtml(t.basis)}</p></section>
    <section><h4>近期记录概况</h4><p>近 7 天记录餐次：早餐 ${dietNumber(records.meal_distribution?.counts?.早餐)}、午餐 ${dietNumber(records.meal_distribution?.counts?.午餐)}、晚餐 ${dietNumber(records.meal_distribution?.counts?.晚餐)}、加餐 ${dietNumber(records.meal_distribution?.counts?.加餐)}；填写进食时间 ${dietNumber(records.meal_distribution?.timed_meals)} 餐，填写分量 ${dietNumber(records.meal_distribution?.meals_with_portion)} 餐。</p><p>饮水记录：${dietNumber(records.hydration?.days_logged)} 天；累计 ${dietNumber(records.hydration?.total_ml)} 毫升；有记录日均 ${dietNumber(records.hydration?.average_on_logged_days_ml)} 毫升。未记录日不作零值处理，也不设统一目标。</p><p>训练日完整碳水均值：${dietNumber(records.training_day_comparison?.training_day_carbs_g)} g（${dietNumber(records.training_day_comparison?.training_days_with_data)} 天）；休息日：${dietNumber(records.training_day_comparison?.rest_day_carbs_g)} g（${dietNumber(records.training_day_comparison?.rest_days_with_data)} 天）。</p></section><section><h4>主要差距与提醒</h4>${list(plan.diagnosis)}${plan.warnings?.length ? `<h5>数据质量与安全提醒</h5>${list(plan.warnings)}` : ''}</section>
    <section><h4>每日目标起点</h4><div class="diet-metrics">${metric('能量', t.calories_kcal, ' kcal')}${metric('蛋白质', t.protein_g, ' g')}${metric('碳水', t.carbs_g, ' g')}${metric('脂肪', t.fat_g, ' g')}</div><p>能量占比约：蛋白质 ${dietNumber(t.protein_percent)}%、碳水 ${dietNumber(t.carbs_percent)}%、脂肪 ${dietNumber(t.fat_percent)}%。</p></section>
    <section><h4>体重趋势与目标进度</h4><p>${escapeHtml(weightTrendText)}</p><p>${escapeHtml(weightTargetText)}</p><small>体重数据来源：你记录的体重历史；记录点不足时不计算变化。体重短期波动不能单独说明脂肪或肌肉变化。</small></section>
    <section><h4>分餐安排与食物示例</h4><div class="diet-meal-targets">${(plan.meal_plan || []).map((meal) => `<article><strong>${escapeHtml(meal.name)}</strong><span>${dietNumber(meal.calories_kcal)} kcal</span><small>蛋白质 ${dietNumber(meal.protein_g)}g · 碳水 ${dietNumber(meal.carbs_g)}g · 脂肪 ${dietNumber(meal.fat_g)}g</small><p>${escapeHtml(plan.food_examples?.find((x) => x.meal === meal.name)?.example || '')}</p></article>`).join('')}</div></section>
    <section><h4>现有习惯与调整</h4><p><b>可保留：</b>${escapeHtml(plan.recorded_habits?.keep || '')}</p><p><b>优先调整：</b>${escapeHtml(plan.recorded_habits?.adjust || '')}</p><p>${escapeHtml(plan.execution_context?.cooking_access || '')}；每周外食 ${dietNumber(plan.execution_context?.eating_out_per_week)} 次；执行条件：${escapeHtml(plan.execution_context?.budget_note || '未填写')}。</p></section>
    <section><h4>追踪与计算说明</h4><p>${escapeHtml(plan.tracking?.period || '')}</p>${list(plan.tracking?.next_data)}<details><summary>查看数据假设与边界</summary>${list(plan.assumptions)}</details></section>`
}
async function refreshDietHistory() {
  const result = await api('/api/diet/plan/history')
  renderDietHistory(result.items || [])
  renderDietDashboard()
}
async function generateDietPlan() {
  $('#diet-plan-result').className = 'empty-state'
  $('#diet-plan-result').innerHTML = '<p>正在结合身体档案、训练安排和近期完整饮食记录生成分析…</p>'
  try { renderDietPlan(await api('/api/diet/plan')); await refreshDietHistory() }
  catch (error) { $('#diet-plan-result').innerHTML = `<p>${escapeHtml(error.message)}</p>`; notify(error.message, 'error') }
}
async function refreshDietPage() {
  if (!activeAccount) return
  if (!$('#diet-date').value) $('#diet-date').value = new Date().toISOString().slice(0, 10)
  try { await Promise.all([loadDietProfile(), loadDietTargets(), refreshDietLog(), refreshDietHistory()]) }
  catch (error) { notify(error.message, 'error') }
}
$('#diet-date').value = new Date().toISOString().slice(0, 10)
$('#diet-date').addEventListener('change', () => refreshDietLog().catch((error) => notify(error.message, 'error')))
async function searchDietFoodCatalog() {
  const keyword = $('#diet-food-query').value.trim()
  if (!keyword) { $('#diet-food-query').focus(); $('#diet-food-search-status').textContent = '请先输入食物名称。'; return }
  const button = $('#search-diet-foods')
  button.disabled = true
  button.textContent = '正在查询…'
  $('#diet-food-search-status').textContent = '正在查询薄荷食物库…'
  try {
    const result = await api(`/api/diet/foods/search?keyword=${encodeURIComponent(keyword)}`)
    dietSearchKeyword = keyword
    renderDietFoodResults(result.items || [], keyword)
    if (!(result.items || []).length) $('#diet-food-search-status').textContent = '没有找到结果，请更换关键词。'
  } catch (error) {
    $('#diet-food-search-results').innerHTML = ''
    $('#diet-food-search-status').textContent = error.message
  } finally {
    button.disabled = false
    button.textContent = '查询薄荷食物库'
  }
}
$('#search-diet-foods').addEventListener('click', searchDietFoodCatalog)
$('#diet-food-query').addEventListener('keydown', (event) => { if (event.key === 'Enter') { event.preventDefault(); searchDietFoodCatalog() } })
$('#diet-food-search-results').addEventListener('click', async (event) => {
  const customButton = event.target.closest('[data-add-custom-food]')
  if (customButton) {
    selectedDietFoods.push({ name: dietSearchKeyword, id: '', basis: '', per100: false, macros: { calories_kcal: null, protein_g: null, carbs_g: null, fat_g: null }, grams: 100 })
    updateSelectedDietFoods()
    return
  }
  const button = event.target.closest('[data-diet-food-index]')
  if (!button) return
  const raw = dietSearchResults[Number(button.dataset.dietFoodIndex)]
  if (!raw) return
  button.disabled = true
  $('#diet-food-search-status').textContent = '正在读取薄荷食物详情…'
  let selected = raw
  const foodCode = raw.code || raw.food_code || raw.food_id
  if (foodCode) {
    try {
      const detail = await api(`/api/diet/foods/detail?code=${encodeURIComponent(foodCode)}`)
      selected = detail.food || raw
      $('#diet-food-search-status').textContent = '已读取薄荷食物详情；接口尚未明确营养值的计量基准，因此暂不按克数换算。'
    } catch (error) {
      $('#diet-food-search-status').textContent = `详情读取失败，先使用搜索结果：${error.message}`
    }
  }
  selectedDietFoods.push({ ...normalizeDietFood(selected), grams: 100 })
  updateSelectedDietFoods()
})
$('#diet-selected-foods').addEventListener('change', (event) => {
  const input = event.target.closest('[data-diet-food-grams]')
  if (!input) return
  const food = selectedDietFoods[Number(input.dataset.dietFoodGrams)]
  const grams = Math.max(1, Math.min(3000, Math.round(Number(input.value) || 1)))
  if (food) food.grams = grams
  updateSelectedDietFoods()
})
$('#diet-selected-foods').addEventListener('click', (event) => {
  const button = event.target.closest('[data-remove-diet-food]')
  if (!button) return
  selectedDietFoods.splice(Number(button.dataset.removeDietFood), 1)
  updateSelectedDietFoods()
})
function openDietMealDialog(meal = null) {
  const form = $('#diet-meal-form')
  form.reset()
  selectedDietFoods = []
  dietSearchResults = []
  dietSearchKeyword = ''
  $('#diet-food-search-results').innerHTML = ''
  $('#diet-selected-foods').innerHTML = ''
  $('#diet-food-query').value = ''
  $('#diet-existing-meal-summary').classList.toggle('hidden', !meal)
  $('#diet-existing-meal-summary').textContent = meal ? `当前记录：${meal.description}${meal.portion ? ` · ${meal.portion}` : ''}` : ''
  $('#diet-food-search-status').textContent = '选择食物并填写克数，系统会按可确认的营养基准计算本餐摄入。'
  editingDietMealId = meal?.id ?? null
  if (meal) {
    for (const [name, value] of Object.entries(meal)) {
      const field = form.elements.namedItem(name)
      if (field) field.value = value ?? ''
    }
  } else {
    const recordedTypes = new Set((dietLogData?.items || []).map((item) => item.meal_type))
    const nextType = ['breakfast', 'lunch', 'dinner'].find((type) => !recordedTypes.has(type)) || 'snack'
    form.elements.namedItem('meal_type').value = nextType
  }
  $('#diet-meal-dialog-title').textContent = meal ? '修改餐食' : '记录一餐'
  form.querySelector('[type="submit"]').textContent = meal ? '保存修改' : '保存餐食'
  $('#diet-meal-dialog-date').textContent = dietSelectedDate()
  $('#diet-meal-dialog').showModal()
  requestAnimationFrame(() => $('#diet-food-query').focus())
}
function closeDietMealDialog() { $('#diet-meal-dialog').close() }
$('#diet-insight-action').addEventListener('click', openDietMealDialog)
$('#close-diet-meal-dialog').addEventListener('click', closeDietMealDialog)
$('#diet-meal-dialog').addEventListener('click', (event) => { if (event.target === $('#diet-meal-dialog')) closeDietMealDialog() })
$('#refresh-diet').addEventListener('click', () => refreshDietLog().catch((error) => notify(error.message, 'error')))
$('#refresh-diet-plan-history').addEventListener('click', () => refreshDietHistory().catch((error) => notify(error.message, 'error')))
$('#generate-diet-plan').addEventListener('click', generateDietPlan)
$('#diet-profile-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  try { const result = await api('/api/diet/profile', { method: 'PUT', body: JSON.stringify(dietFormData(event.currentTarget)) }); await loadDietTargets(); notify(result.message || '饮食规划档案已保存。', 'success') }
  catch (error) { notify(error.message, 'error') }
})
$('#edit-diet-targets').addEventListener('click', async () => {
  if (dietTargetInfo?.missing?.some((item) => item.includes('身体档案'))) {
    if (await loadBodyProfile()) openBodyProfileModal()
    return
  }
  const planning = document.querySelector('.diet-planning-fold')
  const profilePanel = $('#diet-profile-panel')
  planning.open = true
  profilePanel.open = true
  profilePanel.scrollIntoView({ behavior: 'smooth', block: 'start' })
})
$('#diet-meal-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const form = event.currentTarget
  const data = dietFormData(form)
  data.log_date = dietSelectedDate()
  if (!String(data.description || '').trim()) {
    notify('请先搜索并选择至少一种食物。', 'error')
    $('#diet-food-query').focus()
    return
  }
  for (const name of ['eaten_at', 'nutrition_source', 'note', 'portion']) {
    if (typeof data[name] === 'string' && !data[name].trim()) data[name] = null
  }
  const hasNutrition = ['calories_kcal', 'protein_g', 'carbs_g', 'fat_g'].some((name) => data[name] != null)
  if (hasNutrition && !data.nutrition_source) {
    notify('填写热量或营养数据时，请选择数据来源（标签/可靠测量或自行估算）。', 'error')
    form.elements.namedItem('nutrition_source').focus()
    return
  }
  try {
    const path = editingDietMealId ? '/api/diet/meal/' + editingDietMealId : '/api/diet/meal'
    const result = await api(path, { method: editingDietMealId ? 'PUT' : 'POST', body: JSON.stringify(data) })
    form.reset(); editingDietMealId = null; closeDietMealDialog()
    notify(result.message || '餐食记录已保存。', 'success')
    await refreshDietLog()
  }
  catch (error) { notify(error.message, 'error') }
})
$('#diet-water-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const data = dietFormData(event.currentTarget); data.log_date = dietSelectedDate()
  try { const result = await api('/api/diet/water', { method: 'POST', body: JSON.stringify(data) }); event.currentTarget.reset(); notify(result.message || '饮水记录已累计。', 'success'); await refreshDietLog() }
  catch (error) { notify(error.message, 'error') }
})
$('#diet-day-complete').addEventListener('change', async (event) => {
  const params = new URLSearchParams({ log_date: dietSelectedDate(), complete: String(event.currentTarget.checked) })
  try { await api(`/api/diet/day-review?${params}`, { method: 'PUT' }); notify('当天记录完整度已更新。', 'success') }
  catch (error) { event.currentTarget.checked = !event.currentTarget.checked; notify(error.message, 'error') }
})
$('#diet-meal-list').addEventListener('click', async (event) => {
  const editButton = event.target.closest('[data-edit-diet-meal]')
  if (editButton) {
    const meal = dietLogData?.items?.find((item) => Number(item.id) === Number(editButton.dataset.editDietMeal))
    if (meal) openDietMealDialog(meal)
    return
  }
  const deleteButton = event.target.closest('[data-delete-diet-meal]')
  if (!deleteButton) return
  try { const result = await api(`/api/diet/meal/${deleteButton.dataset.deleteDietMeal}`, { method: 'DELETE' }); notify(result.message || '餐食记录已删除。', 'success'); await refreshDietLog() }
  catch (error) { notify(error.message, 'error') }
})
