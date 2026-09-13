import Constants from 'expo-constants'

export function getApiBaseUrl(): string {
  if (process.env.EXPO_PUBLIC_API_URL) return process.env.EXPO_PUBLIC_API_URL
  const hostUri =
    Constants.expoConfig?.hostUri ??
    (Constants as Record<string, any>).manifest2?.extra?.expoGo?.debuggerHost
  if (hostUri) {
    const ip = hostUri.split(':')[0]
    return `http://${ip}:8000`
  }
  // Fallback to computer's current local network IP if not on Android emulator
  return 'http://10.57.140.233:8000'
}

export function resolveImageUrl(url: string | null | undefined): string {
  if (!url) return ''
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  const base = getApiBaseUrl().replace(/\/+$/, '')
  const path = url.startsWith('/') ? url : `/${url}`
  return `${base}${path}`
}

export async function apiFetch<T>(path: string, token?: string, init?: RequestInit): Promise<T> {
  const base = getApiBaseUrl()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${base}${path}`, { ...init, headers })
  if (!res.ok) throw new Error((await res.text()) || `Error ${res.status}`)
  return res.json() as Promise<T>
}
