import { describe, expect, it } from 'vitest'
import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import AdminDataValue from '@/components/admin/AdminDataValue.vue'
import { businessEntries, fieldLabel, formatValue, normalizeValue, safeLink } from './adminPresentation'

const render = (value: unknown, field: string, dataset = '') => renderToString(createSSRApp(AdminDataValue, {
  value, field, dataset, exerciseNames: { '8': '高脚杯深蹲', '5': '单臂哑铃划船' },
}))

describe('administrator business display', () => {
  it('renders a weekly training schedule and action names as readable cards and tables', async () => {
    const html = await render({
      goal: 'fitness', training_weekdays: [1, 4, 6], equipment: ['dumbbells'],
      sessions: [{ weekday: 6, title: '周六综合训练', duration_minutes: 45,
        exercises: [{ id: 8, name: '高脚杯深蹲', sets: 3, reps: 12, target_muscles: ['quadriceps'] }] }],
    }, 'plan_data', 'weekly_plans')
    for (const text of ['综合体能', '周一', '周四', '周六', '哑铃', '每日训练安排', '高脚杯深蹲', '3 组', '12 次', '45 分钟', '股四头肌']) expect(html).toContain(text)
    expect(html).toContain('<table')
    expect(html).not.toContain('展开完整内容')
    expect(html).not.toContain('training_weekdays')
    expect(html).not.toContain('&quot;')
  })
  it('renders dated meals and macro values instead of a JSON blob', async () => {
    const html = await render({ target: { calories_kcal: 2000, protein_g: 120 },
      weekly_plan: [{ date: '2026-10-24', day_type: '训练日',
        meals: [{ name: '早餐', example: '燕麦与鸡蛋', calories_kcal: 400, protein_g: 20 }] }] },
    'plan_data', 'diet_plan_snapshots')
    for (const text of ['2026年10月24日', '训练日', '早餐', '燕麦与鸡蛋', '2,000 kcal', '120 g', '400 kcal']) expect(html).toContain(text)
    expect(html).not.toContain('calories_kcal')
  })
  it('renders nested recommendations, evidence and body metric units', async () => {
    const html = await render({ changes: [{ metric: 'waist_cm', label: '腰围', current: 88, previous: 90, change: -2 }],
      training: { completion_rate: 1 }, data_notes: ['记录仍不足'] }, 'report_data', 'report_snapshot')
    for (const text of ['腰围', '88 cm', '90 cm', '-2 cm', '1%', '记录仍不足']) expect(html).toContain(text)
    const advice = await render({ kind: 'reduce', reasons: ['恢复不足'], proposed_plan: {
      sessions: [{ title: '力量日', exercises: [{ name: '高脚杯深蹲', reps: 10 }] }] },
    }, 'recommendation', 'plan_adjustments')
    expect(advice).toContain('降低负担'); expect(advice).toContain('恢复不足'); expect(advice).toContain('高脚杯深蹲')
  })
  it('resolves action references and preserves unknown names as missing rather than inventing them', () => {
    expect(formatValue('exercise_id', 8, { exerciseNames: { '8': '高脚杯深蹲' } })).toBe('高脚杯深蹲')
    expect(formatValue('exercise_id', 999)).toContain('名称未保留')
    expect(formatValue('completion_rate', 0.75, { dataset: 'plan_adjustments' })).toBe('75%')
    expect(formatValue('completion_rate', 75, { dataset: 'report_snapshot' })).toBe('75%')
    expect(fieldLabel('calories_kcal')).toBe('热量')
    expect(formatValue('calories_kcal', 0)).toBe('0 kcal')
    expect(formatValue('protein_g', null)).toBe('未记录')
    expect(formatValue('is_sick', false)).toBe('否')
    expect(formatValue('note', 'pending')).toBe('pending')
    expect(formatValue('cooking_access', 'none')).toBe('不具备烹饪条件')
  })
  it('shows empty and legacy payloads readably and hides internal fingerprints', async () => {
    expect(normalizeValue('{"calories_kcal":1500}', 'plan_data')).toEqual({ calories_kcal: 1500 })
    expect(normalizeValue('{"calories_kcal":1500}', 'note')).toBe('{"calories_kcal":1500}')
    expect(businessEntries({ fingerprint: 'secret', source_fingerprint: 'secret', title: '饮食草案', payload: { calories_kcal: 1500 } })).toHaveLength(2)
    expect(await render([], 'evidence')).toContain('暂无条目')
    const html = await render({ fingerprint: 'internal-secret', title: '饮食草案', payload: { calories_kcal: 1500 } }, 'draft_data')
    expect(html).toContain('1,500 kcal'); expect(html).not.toContain('internal-secret')
  })
  it('escapes user content and permits only explicit http links', async () => {
    const html = await render({ note: '<script>alert(1)</script>' }, 'record')
    expect(html).not.toContain('<script>'); expect(html).toContain('&lt;script&gt;')
    expect(safeLink('javascript:alert(1)')).toBeNull()
    expect(safeLink('https://example.com/training')).toBe('https://example.com/training')
  })
})
