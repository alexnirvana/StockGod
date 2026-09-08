import { useState } from 'react'
import { Dialog } from '../../components/ui/dialog'
import { Link } from 'react-router-dom'
import { Award, BookOpen, Check, FileText, Target, Trophy, UserRound } from 'lucide-react'
import type { State } from '../../lib/types'
import { dateText } from '../../lib/api'
import { Panel, PageHeader } from '../../components/shared'
import { Button } from '../../components/ui/button'

export default function Profile({ state, onReview }: { state: State; onReview: () => void }) {
  const [reflectionsOpen, setReflectionsOpen] = useState(false)
  const completed = state.courses.filter(c => c.completed).length
  return <div><PageHeader eyebrow="LEARNING PROFILE / 学习档案" title="你的每一步，都有迹可循" description="回看已掌握的知识、需要巩固的概念，以及每一次认真思考。" /><div className="profile-banner"><span className="profile-avatar"><UserRound size={42} /></span><div><span className="eyebrow">LEARNER LEVEL {state.player.level}</span><h2>{state.player.name}</h2><p>理解市场，认识自己</p></div><div className="profile-level"><strong>{state.player.xp} <small>XP</small></strong><div className="xp-track"><i style={{ width: (state.player.xp % 50) * 2 + '%' }} /></div><small>距下一等级还需 {50 - state.player.xp % 50} XP</small></div><div className="profile-count"><strong>{completed} / 5</strong><small>已完成章节</small></div></div>
    <div className="profile-grid"><Panel title="知识掌握情况" icon={<Target className="blue" size={20} />}>{state.courses.map(c => <div className="mastery-row" key={c.id}><span className={'mastery-icon ' + (c.completed ? 'teal-text' : '')}>{c.completed ? <Check size={20} /> : <BookOpen size={20} />}</span><div><h3>{c.title}</h3><small>{c.attempts ? '最近正确率 ' + c.last_score + '% · 共练习 ' + c.attempts + ' 次' : '从例子到独立练习，逐步理解'}</small></div><span className={c.review_due ? 'amber-text' : c.completed ? 'teal-text' : 'muted'}>{c.review_due ? '待复习' : c.completed ? '可独立完成' : '未接触'}</span>{!c.locked && <Button variant="ghost" size="sm" asChild><Link to={'/learn/' + c.id}>{c.review_due || c.completed ? '复习' : '学习'}</Link></Button>}</div>)}</Panel><Panel title="我的徽章" icon={<Trophy className="amber-text" size={20} />}><div className="badge-collection">{state.courses.map((c, i) => <div key={c.id} className={!state.rewards.some(r => r.lesson_id === c.id) ? 'unearned' : ''}><span className={'badge-medal ' + (i % 2 ? 'violet' : '')}><Award size={31} /></span><h3>{c.badge}</h3><small>{state.rewards.some(r => r.lesson_id === c.id) ? '已解锁 · +' + c.xp + ' XP' : '完成独立练习后解锁'}</small></div>)}</div></Panel></div>
    <Button className="reflection-open" variant="secondary" onClick={() => setReflectionsOpen(true)}>我的计划与复盘 · {state.reflections.length} 条记录</Button><Dialog wide open={reflectionsOpen} onOpenChange={setReflectionsOpen} title="我的计划与复盘" description="只显示当前账号保存的练习记录。"><Panel title="练习记录" icon={<FileText className="blue" size={20} />} className="reflection-list">{state.reflections.length ? state.reflections.map(r => <article key={r.id}><header><h3>一次练习，一次思考</h3><time>{dateText(r.created_at)}</time></header><h4>交易前计划</h4><p>{r.plan}</p><h4>交易后复盘</h4><p>{r.review}</p></article>) : <div className="empty-state"><FileText size={30} /><h3>把想法写下来，成长会更清晰</h3><p>在课程的“复盘回顾”中保存计划和复盘，它们会一直留在这里。</p><Button variant="secondary" asChild><Link to="/learn">去完成一次练习</Link></Button></div>}</Panel></Dialog>
    <Button className="review-profile-open" variant="secondary" onClick={onReview}>错题与知识复习 · {state.reviews.due} 个待复习 · {state.reviews.scheduled} 个待巩固</Button>
  </div>
}

