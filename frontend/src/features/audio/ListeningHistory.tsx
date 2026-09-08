import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { t, useLocale } from '../../i18n'
import { api, dateText } from '../../lib/api'
import { ErrorNote, Loading } from '../../components/shared'
import { Button } from '../../components/ui/button'
import { audioTime } from './bookmarks'

type Entry = { lesson_id: string; title: string; locale: string; position_ms: number; duration_ms: number; playback_rate: number; updated_at: string }

export default function ListeningHistory() {
  const locale = useLocale()
  const query = useQuery({ queryKey: ['listening', locale], queryFn: () => api<Entry[]>('/listening') })
  if (query.isPending) return <Loading/>
  if (query.error) return <ErrorNote error={query.error}/>
  return <div className="listening-history">
    <p className="muted">{t('收听位置按账号、课程与语言分别保存，听完音频不会代替独立练习。')}</p>
    {!query.data?.length && <p>{t('还没有收听记录。打开课程讲解，点击播放即可开始。')}</p>}
    {query.data?.map(entry => <article key={entry.lesson_id + entry.locale}>
      <div><h3>{entry.title}</h3><p>{entry.locale === 'en' ? 'English' : '简体中文'} · {audioTime(entry.position_ms)} / {audioTime(entry.duration_ms)} · {entry.playback_rate}×</p><small>{dateText(entry.updated_at)}</small></div>
      <Button variant="secondary" size="sm" asChild><Link to={'/learn/' + entry.lesson_id + '?listen=1&audioLocale=' + entry.locale}>{t('继续收听')}</Link></Button>
    </article>)}
  </div>
}
