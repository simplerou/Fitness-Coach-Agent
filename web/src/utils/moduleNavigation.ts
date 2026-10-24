import type { RouteLocationRaw } from 'vue-router'

type Location = { name: unknown; query: Record<string, unknown> }
export type NavItem = { key: string; label: string; to: RouteLocationRaw }
export type NavGroup = { key: string; label: string; icon: 'training' | 'diet' | 'report' | 'settings'; children: NavItem[] }

export const moduleGroups: NavGroup[] = [
  { key: 'training', label: '训练', icon: 'training', children: [
    { key: 'plan', label: '周计划', to: { name: 'plan' } },
    { key: 'plan-history', label: '历史周计划', to: { name: 'plan', query: { view: 'history' } } },
    { key: 'log', label: '训练记录', to: { name: 'log' } },
  ] },
  { key: 'diet', label: '饮食', icon: 'diet', children: [
    { key: 'diet-log', label: '今日日志', to: { name: 'diet' } },
    { key: 'diet-records', label: '饮食规划记录', to: { name: 'diet', query: { tab: 'records' } } },
    { key: 'diet-weekly', label: '一周饮食计划', to: { name: 'diet', query: { tab: 'weekly' } } },
  ] },
  { key: 'report', label: '报告', icon: 'report', children: [
    { key: 'report-trend', label: '趋势', to: { name: 'shaping', query: { tab: 'trend' } } },
    { key: 'report-measurements', label: '体测', to: { name: 'shaping', query: { tab: 'measurements' } } },
    { key: 'report-review', label: '周回顾', to: { name: 'shaping', query: { tab: 'review' } } },
  ] },
]
export const adminGroup: NavGroup = { key: 'admin', label: '管理中心', icon: 'settings', children: [
  { key: 'admin', label: '用户管理', to: { name: 'admin' } },
  { key: 'admin-knowledge', label: 'RAG 知识库', to: { name: 'admin-knowledge' } },
] }

export function dietModule(query: Location['query']): 'log' | 'records' | 'weekly' {
  return query.tab === 'records' || query.tab === 'weekly' ? query.tab : 'log'
}
export function reportModule(query: Location['query']): 'trend' | 'measurements' | 'review' {
  if (query.tab === 'trend' || query.tab === 'measurements' || query.tab === 'review') return query.tab
  if (query.section === 'measurements' || query.section === 'photos') return 'measurements'
  if (query.section === 'reports' || query.section === 'coach') return 'review'
  return 'trend'
}
export function activeModuleKey(route: Location): string {
  if (route.name === 'plan') return route.query.view === 'history' ? 'plan-history' : 'plan'
  if (route.name === 'diet') return 'diet-' + dietModule(route.query)
  if (route.name === 'shaping') return 'report-' + reportModule(route.query)
  if (route.name === 'review') return 'report-review'
  return String(route.name)
}
export function moduleTitle(route: Location): string {
  const key = activeModuleKey(route)
  return [...moduleGroups, adminGroup].flatMap(group => group.children).find(item => item.key === key)?.label
    || ({ today: '概览', library: '动作库', profile: '设置' }[String(route.name)] || '青禾训练助理')
}
