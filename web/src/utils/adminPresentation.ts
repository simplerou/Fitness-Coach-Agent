import { equipmentLabel, exerciseNameLabel, muscleLabel } from './exerciseLabels'

const baseFields: Record<string, string> = {
  id: '记录编号', registered_on: '建档日期', recorded_on: '记录日期', created_at: '创建时间',
  updated_at: '更新时间', resolved_at: '处理时间', training_date: '训练日期', checkin_date: '恢复日期',
  log_date: '记录日期', signal_date: '状态日期', week_start: '周起始日', generated_on: '生成日期',
  source_week_start: '依据周', target_week_start: '目标周', adjustment_date: '调整日期',
  age_band: '年龄段', age_years: '年龄', biological_sex: '生理性别', height_cm: '身高 / cm',
  weight_kg: '体重或负重 / kg', target_weight_kg: '目标体重 / kg', body_fat_percent: '体脂率 / %',
  waist_cm: '腰围 / cm', hip_cm: '臀围 / cm', chest_cm: '胸围 / cm', arm_cm: '臂围 / cm',
  thigh_cm: '大腿围 / cm', skeletal_muscle_kg: '骨骼肌 / kg', composition_source: '体成分来源',
  readiness: '主观状态', sleep_hours: '睡眠 / 小时', resting_hr: '静息心率', completion: '完成情况',
  rpe: '主观用力程度 RPE', skip_reason: '未完成原因', note: '备注', planned_session_title: '计划训练名称',
  goal: '目标', days_per_week: '每周训练天数', weekdays: '训练星期', experience_level: '训练经验',
  equipment: '器械', session_minutes: '单次时长 / 分钟', preferred_exercise_ids: '偏好动作编号',
  plan_data: '计划内容', exercise_id: '动作编号', log_id: '训练日志编号', sets: '组数', reps: '每组次数',
  target_reps_min: '目标次数下限', target_reps_max: '目标次数上限', soreness: '酸痛度',
  sleep_quality: '睡眠质量', energy: '精神状态', is_sick: '是否生病', warning_symptom: '疼痛信号',
  status: '状态', message: '说明', advice_type: '建议类型', prescription: '建议内容',
  evidence: '数据依据', reason: '理由', recommendation: '调整建议', meal_type: '餐次',
  description: '内容', portion: '份量', eaten_at: '进食时间', calories_kcal: '热量 / kcal',
  protein_g: '蛋白质 / g', carbs_g: '碳水 / g', fat_g: '脂肪 / g', nutrition_source: '营养来源',
  amount_ml: '饮水 / ml', complete: '全天是否完整', activity_level: '活动水平', training_type: '训练类型',
  training_time: '训练开始时间', training_end_time: '训练结束时间', dietary_preference: '饮食偏好',
  allergies: '过敏源', allergies_reviewed: '已确认过敏信息', avoid_foods: '忌口', medical_conditions: '健康情况',
  injuries: '伤病情况', health_reviewed: '已确认健康信息', cooking_access: '烹饪条件',
  eating_out_per_week: '每周外食次数', budget_note: '预算与条件', water_target_ml: '饮水参考目标 / ml',
  muscle_mass_kg: '肌肉量 / kg', measured_bmr: '实测 BMR', measured_tdee: '实测 TDEE', metric: '目标指标',
  baseline_value: '基线值', baseline_date: '基线日期', target_value: '目标值', milestones: '里程碑',
  view: '照片视角', question: '问题', answer: '回答', intent: '意图', exercise_ids: '引用动作编号',
  used_llm: '是否使用模型', action_type: '草案类型', payload: '草案内容', source_fingerprint: '来源标识',
  expires_at: '有效期', hold_active: '安全暂停', hold_date: '暂停日期',
}
export const fieldLabels: Record<string, string> = {
  ...baseFields,
  category: '动作部位', username: '用户名', display_name: '昵称', is_admin: '管理员权限',
  preferred_exercise_ids: '偏好动作', exercise_ids: '引用动作', referenced_exercise_ids: '引用动作',
  exercise_id: '训练动作', exercise_name: '动作名称', name: '名称', title: '标题',
  source_fingerprint: '来源标识', kind: '调整类型', draft_data: '草案详情', advice_data: '建议详情',
  report_data: '报告内容', period_type: '报告周期', period_start: '开始日期', period_end: '结束日期',
  generated_at: '生成时间', hold_requires_professional_confirmation: '恢复前需确认专业意见',
  trigger: '触发原因', focus: '训练重点', focus_groups: '侧重肌群', excluded_groups: '排除肌群',
  sessions: '每日训练安排', exercises: '训练动作', training_weekdays: '训练日', rest_weekdays: '休息日',
  day: '星期', weekday: '星期', target_weekday: '建议训练日', target_day_label: '建议训练日',
  duration_minutes: '训练时长', body_profile_context: '制定计划时的身体数据',
  personal_profile_used: '已使用身体档案', notice: '执行提醒', reps_range: '次数范围',
  volume_multiplier: '训练量系数', deload: '是否减载', target_muscles: '目标肌群',
  summary: '摘要', status: '状态', missing: '待补充信息', target: '参考目标',
  hydration: '饮水情况', target_ml: '饮水参考目标', suggested_ml: '饮水参考量',
  source: '数据来源', basis: '计算依据', warnings: '注意事项', target_note: '目标说明',
  bmr_kcal: '基础代谢', tdee_kcal: '每日总消耗', bmr_source: '基础代谢来源', tdee_source: '总消耗来源',
  bmi: 'BMI', bmi_adult_reference: '成人 BMI 参考', protein_percent: '蛋白质供能占比',
  carbs_percent: '碳水供能占比', fat_percent: '脂肪供能占比', protein_was_capped: '已应用蛋白质上限',
  record_summary: '近期记录汇总', coverage: '记录覆盖情况', averages: '完整记录日均摄入',
  complete_day_averages: '完整记录日均摄入', calories: '热量', protein: '蛋白质', carbs: '碳水', fat: '脂肪',
  training_day_comparison: '训练日与休息日对比', meal_distribution: '各餐摄入分布',
  training_timing_review: '饮食与训练时间', diagnosis: '记录观察', ai_advice: '饮食执行建议',
  change_summary: '本次调整说明', weekly_plan: '每日饮食安排', meal_plan: '分餐参考目标',
  food_examples: '餐食搭配', execution_context: '执行条件', recorded_habits: '饮食习惯',
  tracking: '后续追踪', assumptions: '使用说明', keep: '建议保持', adjust: '优先调整',
  habit_to_keep: '建议保持的习惯', priority_adjustment: '优先调整', tracking_period: '追踪周期',
  next_data: '下次需记录的信息', period: '观察周期', meal: '餐次', meals: '当日餐食',
  example: '食物搭配与分量', foods: '食物', day_index: '计划天数', date: '日期',
  day_type: '当日安排', planning_days: '计划日期', items: '详细条目',
  frequency_days_per_week: '每周训练天数', training_days: '训练天数或安排',
  recent_meals: '近期餐食', previous_plan: '上一版计划',
  meal_macro_targets_calculated_by_backend: '分餐参考目标', verified_observations: '已核对的观察',
  water_days_logged: '饮水记录天数', days_logged: '记录天数', days_with_meals: '有餐食记录的天数',
  days_marked_complete: '已标记完整的天数', days_with_complete_nutrition: '营养数据完整的天数',
  days_with_each_metric: '各营养指标的有效天数', window_days: '观察窗口',
  meals_with_portion: '有份量信息的餐食数', timed_meals: '有时间信息的餐食数',
  repeated_meals: '重复出现的餐食', counts: '记录数量', count: '数量',
  kcal_complete: '热量数据完整天数', protein_complete: '蛋白质数据完整天数',
  carbs_complete: '碳水数据完整天数', fat_complete: '脂肪数据完整天数',
  training_day_carbs_g: '训练日平均碳水', rest_day_carbs_g: '休息日平均碳水',
  training_days_with_data: '有记录的训练日', rest_days_with_data: '有记录的休息日',
  training_days_with_complete_logs: '完整记录的训练日', days_with_meal_time_data: '有餐食时间的天数',
  days_last_meal_over_4h_before_training: '距训练前一餐超过4小时的天数',
  total_ml: '累计饮水', average_on_logged_days_ml: '有记录日平均饮水',
  calculation: '计算说明', basis_calories_kcal: '基础热量目标', intensity: '训练强度',
  changed: '调整内容', reasons: '调整依据', unchanged: '保持不变', proposed_plan: '调整后的计划',
  stats: '依据数据', completion_rate: '完成率', average_rpe: '平均 RPE',
  recovery_status: '恢复状态', has_warning_symptom: '是否存在疼痛信号',
  consecutive_training_weeks: '连续训练周数', tracked_exercises: '已记录动作数',
  progressed_exercises: '产生进阶建议的动作数', replacement: '动作替换', from: '原动作', to: '替代动作',
  planned_days_due: '已到来的计划日', planned_days_evaluated: '纳入统计的计划日',
  unrecorded_plan_days: '尚未记录的计划日', week_in_progress: '本周尚未结束',
  muscle_group: '肌群', frequency: '训练频次', total_sets: '累计组数', weekly_sets: '每周平均组数',
  total_reps: '累计次数', coverage_percent: '训练量占比', mean_coverage_percent: '平均训练量占比',
  integration: '安排方式', weak_groups: '待加强肌群', observed_weeks: '观察周数',
  label: '指标', metric: '指标', current: '本期数值', previous: '上期数值', change: '变化',
  change_kg: '体重变化', changes: '各项指标变化', current_date: '本期测量日期',
  previous_date: '上期测量日期', measurement_count: '测量次数', measurements: '体测变化',
  record_count: '记录数量', log_count: '训练日志数量', training: '训练情况', weight: '体重情况',
  trend: '变化记录', performance: '训练进展', highlights: '进阶记录', type: '进阶方式',
  recovery: '恢复情况', checkin_count: '打卡次数', average_soreness: '平均酸痛度',
  average_sleep_hours: '平均睡眠', insufficient_days: '恢复需关注的天数',
  weak_part_progress: '薄弱部位进展', next_actions: '后续行动', data_notes: '样本说明',
  sample_status: '样本情况', weight_trend_14d: '近14天体重记录', weight_change_14d: '近14天体重变化',
  impact: '影响范围', details: '具体说明', payload: '目标与执行内容', target_date: '目标日期',
  action: '调整内容', recommendation: '调整建议', plan: '训练计划', suggestion: '参考建议',
}
const statuses: Record<string, string> = {
  good: '良好', okay: '一般', poor: '较差', ready: '可用', pending: '待处理',
  proposed: '待采纳', adopted: '已采纳', ignored: '已忽略', expired: '已过期',
  cancelled: '已取消', completed: '按计划完成', partial: '部分完成', skipped: '未进行',
  attention: '需要关注', insufficient: '数据或恢复不足', insufficient_data: '数据不足',
  sufficient: '样本充足', rest: '休息', stop: '暂停训练', unknown: '未知',
  not_recorded: '未记录', recorded: '已记录', no_plan: '暂无计划', legacy_plan: '旧版计划',
  training: '训练', rest_day: '休息日', local: '本地', success: '成功', error: '失败',
}
const enums: Record<string, Record<string, string>> = {
  biological_sex: { male: '男性', female: '女性', unspecified: '未说明' },
  age_band: { under_18: '未满18岁', '18_29': '18–29岁', '30_44': '30–44岁', '45_59': '45–59岁', '60_plus': '60岁及以上' },
  goal: { fitness: '综合体能', strength: '力量基础', fat_loss: '减脂', muscle_gain: '增肌', maintain: '维持体重', body_shape: '身体塑形', performance: '运动表现', whole_body: '全身均衡', shoulders_back: '肩背塑形', glutes_legs: '臀腿塑形' },
  experience_level: { beginner: '刚开始训练', some_experience: '有一定经验', experienced: '训练经验丰富' },
  activity_level: { sedentary: '久坐', light: '轻度活动', moderate: '中等活动', active: '较高活动', very_active: '高活动' },
  training_type: { strength: '力量训练', cardio: '有氧训练', mixed: '混合训练', other: '其他训练' },
  meal_type: { breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '加餐' },
  nutrition_source: { estimate: '自行估算', label: '包装标签' },
  composition_source: { manual: '手动填写', scale_reading: '体脂秤读数', professional_measurement: '专业测量' },
  cooking_access: { none: '不具备烹饪条件', basic: '可简单烹饪', full: '可正常烹饪' },
  warning_symptom: { none: '没有疼痛信号', joint_pain: '关节疼痛', sharp_pain: '锐痛', swelling: '肿胀' },
  skip_reason: { no_time: '没有时间', too_tired: '过于疲劳', discomfort: '身体不适', other: '其他原因' },
  intensity: { high: '较高强度', regular: '常规强度', recovery: '恢复日', rest: '休息日' },
  day_type: { training: '训练日', rest: '休息日', recovery: '恢复日', unknown: '未设置训练安排' },
  period_type: { week: '周报', month: '月报' },
  kind: { diet_target: '今日饮食目标', plan_adjustment: '下周训练调整', hold: '暂停调整', maintain: '保持安排', reduce: '降低负担', deload: '减载', slight_increase: '小幅进阶', variation: '动作变式' },
  intent: { medical: '健康与疼痛问题', substitution: '替代动作', technique: '动作技术', schedule: '训练安排' },
  view: { front: '正面', side: '侧面', back: '背面' },
  source: { manual: '手动记录', local: '本地规则', weak_part_advice: '薄弱部位建议', training_logs: '训练日志', body_profiles: '身体档案' },
}
const progressTypes: Record<string, string> = { weight: '增加重量', reps: '增加次数', sets: '增加组数' }
const internalFields = new Set(['password_hash', 'password_salt', 'user_id', 'image_data', 'fingerprint', 'source_fingerprint', 'content_hash'])
const structuredFields = new Set(['equipment', 'preferred_exercise_ids', 'exercise_ids', 'referenced_exercise_ids', 'weekdays', 'focus_groups', 'excluded_groups', 'milestones', 'plan_data', 'report_data', 'advice_data', 'draft_data', 'recommendation', 'suggestion', 'prescription', 'evidence', 'payload'])
const exerciseArrays = new Set(['preferred_exercise_ids', 'exercise_ids', 'referenced_exercise_ids'])
const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const dayFields = new Set(['weekday', 'target_weekday', 'weekdays', 'training_weekdays', 'rest_weekdays'])
const percentFields = new Set(['coverage_percent', 'mean_coverage_percent', 'protein_percent', 'carbs_percent', 'fat_percent', 'milestones', 'volume_multiplier'])
const units: Record<string, string> = {
  height_cm: 'cm', waist_cm: 'cm', hip_cm: 'cm', chest_cm: 'cm', arm_cm: 'cm', thigh_cm: 'cm',
  weight_kg: 'kg', target_weight_kg: 'kg', skeletal_muscle_kg: 'kg', muscle_mass_kg: 'kg',
  change_kg: 'kg', weight_change_14d: 'kg', body_fat_percent: '%',
  calories_kcal: 'kcal', calories: 'kcal', bmr_kcal: 'kcal', tdee_kcal: 'kcal', basis_calories_kcal: 'kcal',
  measured_bmr: 'kcal', measured_tdee: 'kcal', protein_g: 'g', carbs_g: 'g', fat_g: 'g',
  protein: 'g', carbs: 'g', fat: 'g', training_day_carbs_g: 'g', rest_day_carbs_g: 'g',
  amount_ml: 'ml', water_target_ml: 'ml', target_ml: 'ml', total_ml: 'ml', suggested_ml: 'ml', average_on_logged_days_ml: 'ml',
  sleep_hours: '小时', average_sleep_hours: '小时', session_minutes: '分钟', duration_minutes: '分钟',
  resting_hr: '次/分钟', sets: '组', total_sets: '组', weekly_sets: '组', reps: '次', total_reps: '次',
  target_reps_min: '次', target_reps_max: '次', frequency: '次', checkin_count: '次', measurement_count: '次',
  consecutive_training_weeks: '周', observed_weeks: '周', training_days: '天', window_days: '天',
  days_last_meal_over_4h_before_training: '天',
}

export interface PresentationContext { dataset?: string; exerciseNames?: Record<string, string>; metric?: string }
export function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}
export function normalizeValue(value: unknown, field: string): unknown {
  if (typeof value === 'string' && structuredFields.has(field) && /^[\s]*[\[{]/.test(value)) {
    try { const parsed: unknown = JSON.parse(value); if (isObject(parsed) || Array.isArray(parsed)) return parsed } catch { /* Keep readable legacy text. */ }
  }
  return value
}
export function fieldLabel(field: string, dataset = ''): string {
  if (field === 'training_days') return dataset === 'report_snapshot' ? '训练天数' : '训练日'
  if (field === 'weight_kg') return ['body_profiles', 'body_weight_history'].includes(dataset) ? '体重' : '重量'
  const label = fieldLabels[field]
  return label ? label.replace(/ \/ .+$/, '') : (/^\d{4}-\d{2}-\d{2}$/.test(field) ? formatDateValue(field) : muscleLabel(field).replaceAll('_', ' '))
}
export function businessEntries(value: Record<string, unknown>, omit: string[] = []): [string, unknown][] {
  return Object.entries(value).filter(([key]) => !internalFields.has(key) && !omit.includes(key) &&
    !(key === 'id' && (typeof value.name === 'string' || typeof value.title === 'string')) &&
    !(key === 'metric' && typeof value.label === 'string'))
}
export function formatDateValue(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (match) return Number(match[1]) + '年' + Number(match[2]) + '月' + Number(match[3]) + '日'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString('zh-CN', { hour12: false })
}
export function formatValue(field: string, value: unknown, context: PresentationContext = {}): string {
  if (value === null || value === undefined || value === '') return '未记录'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if ((exerciseArrays.has(field) || field === 'exercise_id') && (typeof value === 'number' || typeof value === 'string')) {
    const name = context.exerciseNames?.[String(value)]
    return name ? exerciseNameLabel(name) : '动作名称未保留（编号 ' + value + '）'
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return '未记录'
    if (dayFields.has(field) && Number.isInteger(value) && value >= 1 && value <= 7) return weekdays[value - 1]!
    if (field === 'day_index') return '第' + (value + 1) + '天'
    if (field === 'days_per_week' || field === 'frequency_days_per_week') return value + ' 天/周'
    let number = value
    let suffix = units[field] || ''
    if (field === 'completion_rate') {
      // Reports store percent values; plan adjustment statistics store a 0–1 ratio.
      number = context.dataset === 'report_snapshot' ? value : value * 100
      suffix = '%'
    } else if (percentFields.has(field)) {
      number = field === 'volume_multiplier' ? value * 100 : value
      suffix = '%'
    } else if (['current', 'previous', 'change', 'baseline_value', 'target_value'].includes(field) && context.metric) {
      suffix = units[context.metric] || ''
    }
    const signed = ['change', 'change_kg', 'weight_change_14d'].includes(field) && number > 0 ? '+' : ''
    const rendered = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(number)
    return signed + rendered + (suffix ? (suffix === '%' ? '%' : ' ' + suffix) : '')
  }
  const text = String(value)
  if (/^\d{4}-\d{2}-\d{2}(?:T.*)?$/.test(text)) return formatDateValue(text)
  if (field === 'metric') return fieldLabel(text, context.dataset)
  if (field === 'sample_status') return ({ sufficient: '样本充足', insufficient: '样本不足' } as Record<string, string>)[text] || statuses[text] || text
  if (['status', 'completion', 'readiness', 'recovery_status'].includes(field)) return statuses[text] || text
  if (['advice_type', 'type'].includes(field)) return progressTypes[text] || text
  if (field === 'meal') return enums.meal_type?.[text] || text
  if (field === 'equipment') {
    const label = equipmentLabel(text)
    return label === '其他器械' ? text : label
  }
  if (['target_muscles', 'focus_groups', 'excluded_groups', 'muscle_group', 'category'].includes(field)) return muscleLabel(text)
  if (['name', 'exercise_name', 'exercise'].includes(field)) return exerciseNameLabel(text)
  return enums[field]?.[text] || text
}
export function listField(field: string): string {
  return ['weekdays', 'training_weekdays', 'rest_weekdays', 'training_days'].includes(field) ? 'weekday' : field
}
export function itemHeading(value: unknown, index: number, field: string, dataset = ''): string {
  if (!isObject(value)) return fieldLabel(field, dataset) + ' ' + (index + 1)
  const title = [value.title, value.name, value.exercise_name, value.planned_session_title].find(item => typeof item === 'string' && item)
  const day = [value.date, value.training_date, value.recorded_on, value.log_date, value.week_start, value.signal_date, value.checkin_date, value.adjustment_date, value.generated_on, value.period_start].find(item => typeof item === 'string' && item)
  const parts = [day ? formatDateValue(String(day)) : '', title ? exerciseNameLabel(String(title)) : ''].filter(Boolean)
  if (parts.length) return parts.join(' · ')
  if (typeof value.meal === 'string' || typeof value.meal_type === 'string') return (typeof value.day_index === 'number' ? '第' + (value.day_index + 1) + '天 · ' : '') + formatValue('meal', value.meal || value.meal_type)
  if (value.day !== undefined || value.weekday !== undefined) return formatValue('weekday', value.day || value.weekday)
  if (typeof value.day_index === 'number') return '第' + (value.day_index + 1) + '天'
  return fieldLabel(field, dataset) + ' ' + (index + 1)
}
export function safeLink(value: unknown): string | null {
  if (typeof value !== 'string' || !/^https?:\/\//i.test(value)) return null
  try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) ? url.href : null } catch { return null }
}
