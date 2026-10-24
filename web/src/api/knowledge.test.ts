import { afterEach, describe, expect, it, vi } from 'vitest'
import { indexKnowledge, listKnowledge, uploadKnowledge } from './knowledge'
import { MAX_KNOWLEDGE_BYTES, validateKnowledgeFile } from '@/utils/knowledgeUpload'

afterEach(() => { vi.unstubAllGlobals() })

describe('knowledge library document requests', () => {
  it('uploads the original file as multipart without forcing a JSON content type', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ document: {}, message: 'saved' })))
    vi.stubGlobal('fetch', fetcher)
    const file = new File(['训练正文'], '训练指南.txt', { type: 'text/plain' })
    await uploadKnowledge(file, { title: '  训练指南  ', source_name: ' 教练资料 ', source_url: '' })
    const [path, init] = fetcher.mock.calls[0]!
    expect(path).toBe('/api/admin/knowledge/uploads')
    expect(new Headers(init.headers).get('Content-Type')).toBeNull()
    expect(init.credentials).toBe('same-origin')
    expect(init.body).toBeInstanceOf(FormData)
    expect(init.body.get('title')).toBe('训练指南')
    expect(init.body.get('source_name')).toBe('教练资料')
    expect(init.body.get('source_url')).toBeNull()
    expect(init.body.get('file').name).toBe('训练指南.txt')
    expect(await init.body.get('file').text()).toBe('训练正文')
  })
  it('requires explicit cloud permission before sending any indexing request', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ document: {}, message: 'indexed' })))
    vi.stubGlobal('fetch', fetcher)
    await expect(indexKnowledge(7, false)).rejects.toThrow('请先确认')
    expect(fetcher).not.toHaveBeenCalled()
    await indexKnowledge(7, true)
    const [path, init] = fetcher.mock.calls[0]!
    expect(path).toBe('/api/admin/knowledge/uploads/7/index')
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/json')
    expect(JSON.parse(init.body)).toEqual({ cloud_consent: true })
  })
  it('keeps title searches encoded and selects a document category', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], total: 0 })))
    vi.stubGlobal('fetch', fetcher)
    await listKnowledge('训练 & 恢复', 'uploaded', 2)
    const url = new URL(fetcher.mock.calls[0]![0], 'http://localhost')
    expect(url.searchParams.get('q')).toBe('训练 & 恢复')
    expect(url.searchParams.get('kind')).toBe('uploaded')
    expect(url.searchParams.get('page')).toBe('2')
  })
  it('validates supported formats, empty files and the upload size boundary', () => {
    expect(validateKnowledgeFile(null)).toContain('选择')
    expect(validateKnowledgeFile({ name: 'file.doc', size: 100 })).toContain('DOCX')
    expect(validateKnowledgeFile({ name: 'file.pdf', size: 0 })).toContain('空')
    expect(validateKnowledgeFile({ name: 'file.pdf', size: MAX_KNOWLEDGE_BYTES + 1 })).toContain('10 MB')
    for (const name of ['guide.TXT', 'guide.md', 'guide.pdf', 'guide.docx']) {
      expect(validateKnowledgeFile({ name, size: MAX_KNOWLEDGE_BYTES })).toBeNull()
    }
  })
})
