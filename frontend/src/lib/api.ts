import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { State } from './types'

let activeUserId = 'anonymous'
export const setActiveUser = (id: string) => { activeUserId = id }
export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message) }
}

export async function api<T>(path: string, body?: unknown, key?: string): Promise<T> {
  const response = await fetch('/api' + path, {
    method: body === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json', 'Idempotency-Key': key || crypto.randomUUID(), 'X-StockGod-Client': 'web', 'X-CSRF-Token': document.cookie.split('; ').find(c => c.startsWith('stockgod_csrf='))?.split('=')[1] || '' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await response.json().catch(() => ({ detail: '服务返回了无法读取的内容，请检查后端是否启动。' }))
  if (!response.ok) {
    const message = Array.isArray(data.detail) ? data.detail.map((x: { msg: string }) => x.msg.replace('Value error, ', '')).join('；') : data.detail
    if (response.status === 401 && !path.startsWith('/auth/')) window.dispatchEvent(new Event('stockgod:unauthorized'))
    throw new ApiError(message || '请求失败，请稍后重试。', response.status)
  }
  return data
}

export const useStateQuery = () => useQuery({ queryKey: ['state'], queryFn: () => api<State>('/state'), refetchInterval: 60000 })

export function useAction<T, V>(path: string) {
  const client = useQueryClient()
  return useMutation({ mutationFn: async (value: V) => {
    // Keep the intent key after an uncertain response, including page refresh.
    // Only the server can decide whether that intent has already taken effect.
    const storageKey = 'stockgod.pending:' + activeUserId + ':' + path
    const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(value)))
    const fingerprint = Array.from(new Uint8Array(bytes)).map(b => b.toString(16).padStart(2, '0')).join('')
    let pending: { fingerprint: string; key: string } | null = null
    try { pending = JSON.parse(sessionStorage.getItem(storageKey) || 'null') } catch { /* invalid saved key */ }
    if (pending?.fingerprint !== fingerprint) pending = { fingerprint, key: crypto.randomUUID() }
    sessionStorage.setItem(storageKey, JSON.stringify(pending))
    const result = await api<T>(path, value, pending!.key)
    if (sessionStorage.getItem(storageKey) === JSON.stringify(pending)) sessionStorage.removeItem(storageKey)
    return result
  }, onSuccess: () => client.invalidateQueries() })
}

export function formatMoney(value: string | number) {
  return Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
export function dateText(value: string) { return new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }
