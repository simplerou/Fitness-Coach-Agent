export const MAX_KNOWLEDGE_BYTES = 10 * 1024 * 1024
export function validateKnowledgeFile(file: { name: string; size: number } | null): string | null {
  if (!file) return '请先选择需要上传的文档。'
  if (!/\.(txt|md|pdf|docx)$/i.test(file.name)) return '仅支持 TXT、Markdown、PDF 和 Word（DOCX）。'
  if (!file.size) return '文件为空，请选择包含文字的文档。'
  if (file.size > MAX_KNOWLEDGE_BYTES) return '单个文件不能超过10 MB。'
  return null
}
export function documentSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
export const knowledgeKindLabels: Record<string, string> = { exercise: '动作资料', external: '公开资料', uploaded: '上传文档' }
export const knowledgeIndexLabels: Record<string, string> = {
  not_indexed: '待生成语义索引', indexing: '语义索引生成中', indexed: '语义索引已就绪',
  failed: '语义索引需重试', outdated: '语义索引需更新', managed: '由现有知识索引维护',
}
