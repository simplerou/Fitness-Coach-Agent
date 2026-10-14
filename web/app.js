const $ = (selector) => document.querySelector(selector)
const $$ = (selector) => [...document.querySelectorAll(selector)]
let toastTimer
let safetyStatus = 'ask'

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    const message = typeof body.detail === 'string' ? body.detail : '请求失败，请稍后重试。'
    throw new Error(message)
  }
  return body
}

function notify(message, kind = 'info') {
  const toast = $('#toast')
  toast.textContent = message
  toast.dataset.kind = kind
  toast.classList.add('show')
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3200)
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char])
}

function showPage(name) {
  $$('.tab').forEach((tab) => tab.classList.toggle('active', tab.dataset.page === name))
  $$('.page').forEach((page) => page.classList.toggle('active', page.id === `page-${name}`))
  if (name === 'today') refreshToday()
  if (name === 'log') refreshLogs()
}

$$('.tab').forEach((tab) => tab.addEventListener('click', () => showPage(tab.dataset.page)))
$$('[data-goto]').forEach((button) => button.addEventListener('click', () => showPage(button.dataset.goto)))

function levelLabel(level) {
  return ({
    ask: ['等待筛查', '安全筛查尚未完成'],
    stop: ['暂停训练', '已触发安全暂停'],
    insufficient_data: ['信息不足', '缺少今天的主观状态'],
    normal: ['按计划', '依据你主动提供的信息'],
    downgrade: ['考虑降负荷', '依据你主动提供的信息'],
  })[level] || ['状态未知', '']
}

async function refreshToday() {
  const card = $('#today-card')
  try {
    const result = await api('/api/today')
    const [label, detail] = levelLabel(result.level)
    card.className = `status-card status-${result.level}`
    card.innerHTML = `<div class="status-top"><span class="status-pill"><i></i>${escapeHtml(label)}</span><span class="status-detail">${escapeHtml(detail)}</span></div><h3>${escapeHtml(result.message)}</h3><ul class="reason-list">${(result.reasons || []).map((reason) => `<li>${escapeHtml(reason)}</li>`).join('')}</ul>${result.plan_items?.length ? `<div class="today-items">${result.plan_items.map((item) => `<div><b>${escapeHtml(item.day)} · ${escapeHtml(item.title)}</b><p>${escapeHtml(item.description)}</p></div>`).join('')}</div>` : ''}`
    if (result.level === 'stop') safetyStatus = 'stop'
    if (result.level === 'stop') updateSafetyUi()
  } catch (error) {
    card.className = 'status-card status-ask'
    card.textContent = error.message
  }
}

$('#refresh-today').addEventListener('click', refreshToday)

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
  } catch (error) { notify(error.message, 'error') }
})

$('#plan-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const data = new FormData(event.currentTarget)
  const payload = { goal: data.get('goal'), days_per_week: Number(data.get('days_per_week')) }
  try {
    const result = await api('/api/plan', { method: 'POST', body: JSON.stringify(payload) })
    const plan = result.week_plan
    $('#plan-result').className = 'plan-result'
    $('#plan-result').innerHTML = `<div class="plan-meta"><span>${escapeHtml(plan.focus)}</span><span>每周 ${escapeHtml(plan.days_per_week)} 天</span></div><div class="session-list">${plan.sessions.map((session, index) => `<article class="session"><span class="session-index">0${index + 1}</span><div><b>${escapeHtml(session.day)} · ${escapeHtml(session.title)}</b><p>${escapeHtml(session.description)}</p></div></article>`).join('')}</div><p class="fine-print">${escapeHtml(plan.notice)}</p>`
    $('#plan-summary').className = 'plan-summary-mini'
    $('#plan-summary').innerHTML = `<b>${escapeHtml(plan.focus)} · 每周 ${escapeHtml(plan.days_per_week)} 天</b><p>${plan.sessions.map((session) => escapeHtml(session.title)).join(' / ')}</p><button class="text-button" data-goto="plan">查看计划 →</button>`
    $('#plan-summary [data-goto]').addEventListener('click', () => showPage('plan'))
    notify('本周计划已生成。')
  } catch (error) { notify(error.message, 'error') }
})

$('#log-form').training_date.value = new Date().toLocaleDateString('en-CA')
$('#log-form [name="completion"]').addEventListener('change', (event) => {
  $('#skip-reason-wrap').classList.toggle('hidden', event.target.value !== 'skipped')
})

$('#log-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const data = new FormData(event.currentTarget)
  const payload = { training_date: data.get('training_date'), completion: data.get('completion') }
  if (data.get('rpe')) payload.rpe = Number(data.get('rpe'))
  if (data.get('skip_reason')) payload.skip_reason = data.get('skip_reason')
  if (data.get('note')) payload.note = data.get('note')
  try {
    await api('/api/log', { method: 'POST', body: JSON.stringify(payload) })
    event.currentTarget.reset()
    $('#log-form').training_date.value = new Date().toLocaleDateString('en-CA')
    $('#skip-reason-wrap').classList.add('hidden')
    notify('训练记录已保存。')
    await refreshLogs()
  } catch (error) { notify(error.message, 'error') }
})

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
  } catch (error) { target.textContent = error.message }
}
$('#refresh-logs').addEventListener('click', refreshLogs)

function updateSafetyUi() {
  const held = safetyStatus === 'stop'
  $('#resolution-form').classList.toggle('hidden', !held)
  $('#safety-form').classList.toggle('hidden', held)
}

$('#safety-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const data = new FormData(event.currentTarget)
  const symptoms = data.getAll('symptoms')
  try {
    const result = await api('/api/safety-check', {
      method: 'POST',
      body: JSON.stringify({ completed: Boolean(data.get('completed')), symptoms }),
    })
    safetyStatus = result.status
    updateSafetyUi()
    notify(result.message, result.status === 'stop' ? 'error' : 'info')
    await refreshToday()
  } catch (error) { notify(error.message, 'error') }
})

$('#resolution-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const data = new FormData(event.currentTarget)
  try {
    const result = await api('/api/safety-resolution', {
      method: 'POST',
      body: JSON.stringify({
        confirmed_recovery: Boolean(data.get('confirmed_recovery')),
        followed_professional_advice: Boolean(data.get('followed_professional_advice')),
      }),
    })
    safetyStatus = 'ask'
    event.currentTarget.reset()
    updateSafetyUi()
    notify(result.message)
    await refreshToday()
  } catch (error) { notify(error.message, 'error') }
})

refreshToday()
refreshLogs()
