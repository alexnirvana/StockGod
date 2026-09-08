import type { ReactNode } from 'react'
import { AlertCircle, ArrowRight, Bot, Send, ShieldCheck, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Button } from './ui/button'
import { useAction } from '../lib/api'

export function Panel({ title, icon, action, children, className = '' }: { title?: string; icon?: ReactNode; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={'panel ' + className}>{title && <header className="panel-heading"><h2>{icon}{title}</h2>{action}</header>}{children}</section>
}
export function SimulationBadge() { return <span className="simulation-badge"><ShieldCheck size={15} />仅使用虚拟资金</span> }
export function ErrorNote({ error }: { error?: Error | null }) { return error ? <div className="error-note" role="alert"><AlertCircle size={18} />{error.message}</div> : null }
export function Loading() { return <div className="loading-state" role="status"><span className="spinner" />正在读取你的学习空间…</div> }
export function PageHeader({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children?: ReactNode }) {
  return <header className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{children || <SimulationBadge />}</header>
}
export function Coach({ lessonId = 'account', compact = false }: { lessonId?: string; compact?: boolean }) {
  const [question, setQuestion] = useState('')
  const mutation = useAction<{ answer: string; source: string }, { question: string; lesson_id: string }>('/coach')
  const ask = (text: string) => { if (text.trim()) mutation.mutate({ question: text, lesson_id: lessonId }) }
  return <Panel title="AI 教练" icon={<Bot className="blue" />} className={'coach ' + (compact ? 'compact' : '')} action={<span className="tiny muted">预设教学讲解</span>}>
    {!mutation.data && <div className="coach-prompts">{[['解释这一步', '用简单的话，理解当前概念'], ['为什么没有成交？', '查看委托和成交之间的区别'], ['再给一个例子', '换个情景，巩固刚学到的知识']].map(([title, desc], i) =>
      <button className="coach-prompt" key={title} onClick={() => ask(title)}><span className={'orb ' + (i === 2 ? 'teal' : '')}><Sparkles size={19} /></span><span><strong>{title}</strong><small>{desc}</small></span><ArrowRight size={15} /></button>)}</div>}
    {mutation.data && <div className="coach-answer" aria-live="polite"><p>{mutation.data.answer}</p><span className="tiny blue">参考：{mutation.data.source}</span><button className="text-link" onClick={() => mutation.reset()}>返回常见问题</button></div>}
    <ErrorNote error={mutation.error} />
    <form className="coach-input" onSubmit={e => { e.preventDefault(); ask(question); setQuestion('') }}><input aria-label="向教练提问" placeholder="想了解什么？例如：什么是可用资金" maxLength={500} value={question} onChange={e => setQuestion(e.target.value)} /><Button size="icon" variant="ghost" disabled={mutation.isPending || !question.trim()} aria-label="发送问题"><Send size={18} /></Button></form>
    {mutation.isPending && <p role="status" className="tiny">正在整理讲解…</p>}
  </Panel>
}

