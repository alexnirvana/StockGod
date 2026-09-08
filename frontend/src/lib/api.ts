import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import type { State } from './types'
import { i18n, t, useLocale } from '../i18n'

let activeUserId = 'anonymous'
export const setActiveUser = (id: string) => { activeUserId = id }
export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message) }
}

export async function api<T>(path: string, body?: unknown, key?: string, options?: { keepalive?: boolean }): Promise<T> {
  const requestUserId = activeUserId
  const response = await fetch('/api' + path, {
    method: body === undefined ? 'GET' : 'POST',
    credentials: 'same-origin', keepalive: options?.keepalive,
    headers: { 'Accept-Language': i18n.language, ...(body === undefined ? {} : { 'Content-Type': 'application/json', 'Idempotency-Key': key || crypto.randomUUID(), 'X-StockGod-Client': 'web', 'X-CSRF-Token': document.cookie.split('; ').find(c => c.startsWith('stockgod_csrf='))?.split('=')[1] || '' }) },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await response.json().catch(() => ({ detail: t('服务返回了无法读取的内容，请检查后端是否启动。') }))
  if (!response.ok) {
    const message = Array.isArray(data.detail) ? data.detail.map((x: { msg: string }) => x.msg.replace('Value error, ', '')).join('；') : data.detail
    if (response.status === 401 && requestUserId === activeUserId && !path.startsWith('/auth/')) window.dispatchEvent(new Event('stockgod:unauthorized'))
    throw new ApiError(message || t('请求失败，请稍后重试。'), response.status)
  }
  return data
}

export const useStateQuery = () => {
  const locale = useLocale()
  return useQuery({ queryKey: ['state', locale], placeholderData: keepPreviousData, queryFn: () => api<State>('/state'), refetchInterval: 60000 })
}

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
  return Number(value).toLocaleString(i18n.language, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
export function dateText(value: string) { return new Date(value).toLocaleString(i18n.language, { timeZone: 'Asia/Shanghai', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }) }
