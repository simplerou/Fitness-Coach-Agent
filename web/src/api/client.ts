export class ApiError extends Error {
  readonly status: number | null

  constructor(message: string, status: number | null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    const headers = new Headers(init.headers)
    if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
    response = await fetch(path, {
      ...init,
      credentials: 'same-origin',
      headers,
    })
  } catch {
    throw new ApiError('网络或服务暂时异常，请稍后重试。', null)
  }

  const body: unknown = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = typeof body === 'object' && body !== null && 'detail' in body
      ? body.detail
      : null
    const message = typeof detail === 'string' ? detail : '请求失败，请稍后重试。'
    throw new ApiError(message, response.status)
  }
  return body as T
}
