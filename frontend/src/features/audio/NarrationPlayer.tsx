import { useLayoutEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Headphones, Pause, Play, RotateCcw } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { t, useLocale } from '../../i18n'
import { api } from '../../lib/api'
import type { AuthUser, Course } from '../../lib/types'
import { audioTime, BookmarkWriter, type Bookmark } from './bookmarks'

export type Narration = { id: string; locale: string; version: string; url: string; duration_ms: number;
  sections: { title: string; start_ms: number }[]; course_id?: string; owner_id?: string; bookmark?: Bookmark }

export default function NarrationPlayer({ narration }: { narration: Narration }) {
  useLocale()
  const audio = useRef<HTMLAudioElement>(null)
  const alive = useRef(true)
  const touched = useRef(false)
  const lastCheckpoint = useRef(0)
  const initial = useRef(narration.bookmark || { position_ms: 0, playback_rate: 1, revision: 0 })
  const identity = useRef(crypto.randomUUID())
  const client = useQueryClient()
  const [position, setPosition] = useState(initial.current.position_ms)
  const [rate, setRate] = useState(initial.current.playback_rate)
  const [playing, setPlaying] = useState(false)
  const [waiting, setWaiting] = useState(false)
  const [audioError, setAudioError] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [saved, setSaved] = useState(false)
  const [writer] = useState(() => narration.bookmark && narration.course_id && narration.owner_id ? new BookmarkWriter(initial.current,
    (body, key) => api<Bookmark>('/courses/' + narration.course_id + '/listening', {
      ...body, owner_id: narration.owner_id, locale: narration.locale, version: narration.version,
    }, key, { keepalive: true }),
    bookmark => {
      if (client.getQueryData<{ user: AuthUser }>(['auth'])?.user.id === narration.owner_id) {
        client.setQueryData<Course>(['course', narration.course_id, narration.locale], old => old?.narration ? { ...old, narration: { ...old.narration, bookmark } } : old)
        client.setQueryData<Narration>(['narration', narration.course_id, narration.locale], old => old ? { ...old, bookmark } : old)
        void client.invalidateQueries({ queryKey: ['listening'] })
      }
      if (alive.current) { setSaveError(''); setSaved(true) }
    }, error => { if (alive.current) setSaveError(error.message) }) : undefined)

  const checkpoint = () => {
    const element = audio.current
    if (!element || !touched.current || !Number.isFinite(element.currentTime)) return
    lastCheckpoint.current = Date.now()
    void writer?.save({ position_ms: Math.min(narration.duration_ms, Math.round(element.currentTime * 1000)), playback_rate: element.playbackRate })
  }
  useLayoutEffect(() => {
    alive.current = true
    const element = audio.current!
    const otherPlayer = (event: Event) => { if ((event as CustomEvent).detail !== identity.current) element.pause() }
    window.addEventListener('stockgod:narration-play', otherPlayer)
    window.addEventListener('pagehide', checkpoint)
    return () => {
      alive.current = false
      checkpoint()
      element.pause()
      window.removeEventListener('stockgod:narration-play', otherPlayer)
      window.removeEventListener('pagehide', checkpoint)
    }
  }, [])

  const play = async () => {
    const element = audio.current!
    if (playing) { element.pause(); return }
    touched.current = true
    setAudioError(false)
    setWaiting(true)
    window.dispatchEvent(new CustomEvent('stockgod:narration-play', { detail: identity.current }))
    if (element.error) element.load()
    if (element.ended || element.currentTime >= narration.duration_ms / 1000 - .2) element.currentTime = 0
    try { await element.play() }
    catch { if (alive.current) { setAudioError(true); setWaiting(false); setPlaying(false) } }
  }
  const seek = (ms: number) => {
    if (!audio.current || audio.current.readyState === 0) return
    touched.current = true
    audio.current.currentTime = Math.min(ms / 1000, audio.current.duration)
    setPosition(ms)
    setSaved(false)
  }
  const section = narration.sections.filter(section => section.start_ms <= position).at(-1)
  return <section className="narration-player" aria-label={t('语音讲解')}>
    <audio ref={audio} src={narration.url} preload="metadata"
      onLoadedMetadata={() => { const element = audio.current!; element.currentTime = Math.min(initial.current.position_ms / 1000, element.duration); element.playbackRate = rate }}
      onPlaying={() => { setPlaying(true); setWaiting(false) }} onWaiting={() => setWaiting(true)}
      onPause={() => { if (alive.current) { setPlaying(false); setWaiting(false) }; checkpoint() }}
      onEnded={() => { setPlaying(false); setWaiting(false); checkpoint() }}
      onError={() => { setAudioError(true); setPlaying(false); setWaiting(false) }}
      onSeeked={checkpoint}
      onTimeUpdate={() => { const element = audio.current!; setPosition(Math.round(element.currentTime * 1000)); if (!element.paused && !element.seeking && Date.now() - lastCheckpoint.current >= 10000) checkpoint() }}/>
    <div className="narration-heading"><Headphones size={18}/><strong>{t('语音讲解')}</strong><small>{t('内置合成语音')}</small></div>
    <div className="narration-controls">
      <Button type="button" size="sm" onClick={() => void play()} aria-label={playing ? t('暂停讲解') : t('播放讲解')}>
        {playing ? <Pause size={16}/> : <Play size={16}/>} {playing ? t('暂停讲解') : t('播放讲解')}
      </Button>
      <Button type="button" variant="ghost" size="icon" aria-label={t('从头播放')} onClick={() => { seek(0); if (!playing) void play() }}><RotateCcw size={16}/></Button>
      <label className="narration-rate">{t('语速')}<select aria-label={t('语速')} value={rate} onChange={e => {
        const next = Number(e.target.value); touched.current = true; setRate(next); audio.current!.playbackRate = next; setSaved(false); checkpoint()
      }}>{[.75, 1, 1.25, 1.5, 2].map(value => <option key={value} value={value}>{value}×</option>)}</select></label>
      <span className="narration-time">{audioTime(position)} / {audioTime(narration.duration_ms)}</span>
    </div>
    <input className="narration-seek" type="range" aria-label={t('收听位置')} aria-valuetext={audioTime(position)} min={0} max={narration.duration_ms} step={1000} value={Math.min(position, narration.duration_ms)} onChange={e => seek(Number(e.target.value))}/>
    <div className="narration-footer">
      {narration.sections.length > 1 && <select aria-label={t('跳转讲解段落')} value={section?.start_ms || 0} onChange={e => seek(Number(e.target.value))}>{narration.sections.map(section => <option key={section.start_ms} value={section.start_ms}>{section.title}</option>)}</select>}
      <span role="status">{waiting ? t('正在加载音频…') : saved ? t('收听位置已保存') : writer ? t('自动保存收听位置') : t('点击播放收听讲解')}</span>
    </div>
    {audioError && <p className="audio-error" role="alert">{t('音频暂时无法播放，请检查声音设置或网络后再次点击播放。')}</p>}
    {saveError && <div className="audio-error" role="alert">{saveError}<button type="button" className="text-link" onClick={() => void writer?.retry()}>{t('重试保存')}</button></div>}
  </section>
}
