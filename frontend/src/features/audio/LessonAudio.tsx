import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { t, useLocale, type Locale } from '../../i18n'
import { api } from '../../lib/api'
import { ErrorNote, Loading } from '../../components/shared'
import NarrationPlayer, { type Narration } from './NarrationPlayer'

export default function LessonAudio({ lessonId, initial, requestedLocale }: { lessonId: string; initial?: Narration | null; requestedLocale?: string | null }) {
  const locale = useLocale()
  const [spokenLocale, setSpokenLocale] = useState(requestedLocale === 'en' || requestedLocale === 'zh-CN' ? requestedLocale : locale)
  const query = useQuery({ queryKey: ['narration', lessonId, spokenLocale], queryFn: () => api<Narration>('/courses/' + lessonId + '/narration?locale=' + spokenLocale),
    initialData: initial?.locale === spokenLocale ? initial : undefined, staleTime: 0 })
  return <div className="lesson-audio"><label className="narration-language">{t('朗读语言')}<select aria-label={t('朗读语言')} value={spokenLocale} onChange={e => setSpokenLocale(e.target.value as Locale)}><option value="zh-CN">简体中文</option><option value="en">English</option></select></label>
    {query.isPending ? <Loading/> : query.error ? <ErrorNote error={query.error}/> : query.data && <NarrationPlayer key={query.data.id + query.data.locale + query.data.version} narration={query.data}/>}
  </div>
}
