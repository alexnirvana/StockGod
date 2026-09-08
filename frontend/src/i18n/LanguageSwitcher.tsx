import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Languages } from 'lucide-react'
import { api } from '../lib/api'
import type { AuthUser } from '../lib/types'
import { setLocale, t, useLocale, type Locale } from './index'

export default function LanguageSwitcher({ authenticated = false }: { authenticated?: boolean }) {
  const locale = useLocale()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const client = useQueryClient()
  const change = async (next: Locale) => {
    setPending(true); setError('')
    try {
      if (authenticated) {
        const result = await api<{ locale: Locale }>('/preferences/language', { locale: next })
        client.setQueryData<{ user: AuthUser }>(['auth'], old => old ? { user: { ...old.user, locale: result.locale } } : old)
      }
      await setLocale(next)
      if (authenticated) await client.invalidateQueries()
    } catch (e) { setError((e as Error).message) }
    finally { setPending(false) }
  }
  return <div className="language-control"><Languages size={17} /><select aria-label={t('界面语言')} value={locale} disabled={pending} onChange={e => void change(e.target.value as Locale)}><option value="zh-CN">简体中文</option><option value="en">English</option></select>{pending && <span role="status" className="sr-only">{t('正在保存…')}</span>}{error && <span className="language-error" role="alert">{error}</span>}</div>
}
