import { ApiError, request } from './client'
export type KnowledgeKind = 'exercise' | 'external' | 'uploaded'
export type KnowledgeFilter = KnowledgeKind | 'all'
export interface KnowledgeEntry {
  id: number; kind: KnowledgeKind; title: string; source_name: string; source_url: string | null
  review_status: string; created_at: string; characters: number; chunk_count: number
  filename?: string | null; file_type?: string | null; file_size?: number | null
  index_status: string; index_model?: string | null
}
export interface KnowledgeDetail extends KnowledgeEntry {
  body: string; index_error?: string | null; indexed_at?: string | null
  source_published_at?: string | null; tags?: string[]; target_muscles?: string[]; equipment?: string[]
}
export interface KnowledgeSummary { documents: number; uploads: number; segments: number; active_segments: number }
export interface KnowledgePage { items: KnowledgeEntry[]; total: number; page: number; page_size: number; summary: KnowledgeSummary }
export interface KnowledgeMetadata { title: string; source_name: string; source_url: string }
export function listKnowledge(q: string, kind: KnowledgeFilter, page: number, signal?: AbortSignal): Promise<KnowledgePage> {
  return request('/api/admin/knowledge/documents?' + new URLSearchParams({ q, kind, page: String(page), page_size: '20' }), { signal })
}
export function getKnowledge(kind: KnowledgeKind, id: number, signal?: AbortSignal): Promise<KnowledgeDetail> {
  return request('/api/admin/knowledge/' + (kind === 'uploaded' ? 'uploads/' : 'documents/') + id, { signal })
}
export function uploadKnowledge(file: File, metadata: KnowledgeMetadata, signal?: AbortSignal): Promise<{ document: KnowledgeDetail; message: string }> {
  const body = new FormData()
  body.append('file', file)
  for (const [key, value] of Object.entries(metadata)) if (value.trim()) body.append(key, value.trim())
  return request('/api/admin/knowledge/uploads', { method: 'POST', body, signal })
}
export function indexKnowledge(id: number, consent: boolean, signal?: AbortSignal): Promise<{ document: KnowledgeDetail; message: string }> {
  if (!consent) return Promise.reject(new ApiError('请先确认允许云端模型处理本文档文字。', null))
  return request('/api/admin/knowledge/uploads/' + id + '/index', {
    method: 'POST', body: JSON.stringify({ cloud_consent: true }), signal,
  })
}
export const knowledgeFileUrl = (id: number): string => '/api/admin/knowledge/uploads/' + id + '/file'
