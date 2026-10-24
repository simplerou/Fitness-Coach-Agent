import { describe, expect, it } from 'vitest'
import { activeModuleKey, dietModule, moduleGroups, moduleTitle, reportModule } from './moduleNavigation'

describe('module navigation', () => {
  it('matches every sidebar child to its deep link and title', () => {
    for (const group of moduleGroups) for (const child of group.children) {
      const target = child.to as { name: string; query?: Record<string, unknown> }
      const route = { name: target.name, query: target.query || {} }
      expect(activeModuleKey(route)).toBe(child.key)
      expect(moduleTitle(route)).toBe(child.label)
    }
  })
  it('retains legacy report entry points', () => {
    expect(reportModule({ section: 'photos' })).toBe('measurements')
    expect(reportModule({ section: 'coach' })).toBe('review')
    expect(reportModule({ section: 'photos', tab: 'trend' })).toBe('trend')
    expect(activeModuleKey({ name: 'review', query: {} })).toBe('report-review')
  })
  it('falls back safely for unsupported query values', () => {
    expect(dietModule({ tab: 'invalid' })).toBe('log')
    expect(dietModule({ tab: ['weekly'] })).toBe('log')
    expect(reportModule({ tab: 'invalid' })).toBe('trend')
    expect(moduleTitle({ name: 'plan', query: { view: 'history' } })).toBe('历史周计划')
  })
})
