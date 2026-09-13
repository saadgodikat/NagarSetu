export const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

export function resolveImageUrl(url: string | null | undefined): string {
  if (!url) return ''
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  const base = API.replace(/\/+$/, '')
  const path = url.startsWith('/') ? url : `/${url}`
  return `${base}${path}`
}

export async function apiFetch<T>(
  path: string,
  token?: string,
  init?: RequestInit
): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string> | undefined) },
  })
  if (!res.ok) {
    const raw = await res.text()
    let msg = raw
    try {
      const parsed = JSON.parse(raw)
      if (typeof parsed.detail === 'string') {
        msg = parsed.detail
      } else if (Array.isArray(parsed.detail) && parsed.detail[0]?.msg) {
        msg = parsed.detail[0].msg
      }
    } catch {
      // not json
    }
    throw new ApiError(res.status, msg || `Error ${res.status}`)
  }
  return res.json() as Promise<T>
}
