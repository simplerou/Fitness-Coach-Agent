import { request } from './client'
import type { AuthUser } from './types/auth'
export interface AdminUser extends AuthUser { created_at: string }
export interface PageResult<T> { items: T[]; total: number; page: number; page_size: number }
export interface Dataset { key: string; label: string; count: number }
export interface UserDetail { user: AdminUser; datasets: Dataset[] }
export interface RecordPage extends PageResult<Record<string, unknown>> { columns: string[]; exercise_names: Record<string, string> }
export function listAdminUsers(q: string, page: number, signal?: AbortSignal): Promise<PageResult<AdminUser>> {
  return request('/api/admin/users?' + new URLSearchParams({ q, page: String(page), page_size: '20' }), { signal })
}
export function getAdminUser(id: number, signal?: AbortSignal): Promise<UserDetail> {
  return request('/api/admin/users/' + id, { signal })
}
export function getAdminRecords(id: number, dataset: string, page: number, signal?: AbortSignal): Promise<RecordPage> {
  return request('/api/admin/users/' + id + '/records/' + encodeURIComponent(dataset) + '?page=' + page + '&page_size=20', { signal })
}
export function adminPhotoUrl(id: number, photoId: number): string {
  return '/api/admin/users/' + id + '/photos/' + photoId
}
