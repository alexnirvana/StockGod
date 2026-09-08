import { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'motion/react'
import { ArrowRight, Award, BookOpen, Check, ChevronRight, CircleAlert, FileText, Gamepad2, Layers, LockKeyhole, Map, ShieldCheck, Target } from 'lucide-react'
import type { State } from '../../lib/types'
import { formatMoney, dateText } from '../../lib/api'
import { Button } from '../../components/ui/button'
import { Panel, Coach } from '../../components/shared'
import { Dialog } from '../../components/ui/dialog'
import { Chart } from '../../components/Chart'

export default function Home({ state, onStart, onReview }: { state: State; onStart: () => void; onReview: () => void }) {
  const [period, setPeriod] = useState(1)
  const [detail, setDetail] = useState('')
  const completed = state.courses.filter(c => c.completed).length
  const next = state.courses.find(c => !c.completed) || state.courses[state.courses.length - 1]
  const { account, last_attempt: last } = state
  const quote = account.quotes[0]
  return <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="dashboard">
    <div className="dashboard-main">
      <section className="hero" data-tour="welcome">
        <div className="hero-art" /><div className="hero-shade" />
        <div className="hero-copy"><div className="hero-eyebrow"><span className="status-dot" />当前章节 <span>CHAPTER {String(state.courses.indexOf(next) + 1).padStart(2, '0')}</span></div>
          <h1>{completed === 5 ? '学习之后，继续探索' : state.player.onboarded ? next.title : '开启你的投资学习之旅'}</h1>
          <p>从模拟交易开始，理解市场的运行规则，<br />在实践中建立属于自己的交易思维。</p>
          <Button className="hero-button" onClick={onStart}>{state.player.onboarded ? '继续学习' : '开始学习'}<ArrowRight size={23} /></Button>
          <div className="hero-footnote"><ShieldCheck size={13} />虚拟资金练习 · 不进行真实交易</div>
        </div>
        <div className="hero-tag"><span>LEARN. PRACTICE. GROW.</span>成为更好的自己</div>
      </section>
      <div className="quick-cards">
        <Link to="/map" className="quick-card progress-card"><div className="progress-ring" style={{ '--progress': completed * 20 + '%' } as React.CSSProperties}><strong>{completed * 20}<small>%</small></strong></div><div><h2>学习进度</h2><p>已完成 <strong className="teal-text">{completed} / 5</strong> 个章节</p><small>循序学习，解锁更多内容</small></div><ChevronRight size={17} /></Link>
        <button onClick={onReview} className="quick-card review-card"><span className="large-orb amber"><BookOpen size={29} /></span><div><h2>待复习知识</h2><p className="amber-text">{state.reviews.due} 个知识点 · {state.reviews.scheduled} 个待巩固</p><small>换个案例，让理解更扎实</small></div></button>
        <Link to="/simulate" className="quick-card simulation-card" data-tour="practice"><span className="large-orb purple"><Gamepad2 size={32} /></span><div><h2>自由模拟</h2><p>使用虚拟资金自主练习</p><small>在实践中巩固所学知识</small></div></Link>
      </div>
      <div className="feedback-coach compact-feedback">
        <button className="summary-open panel" onClick={() => setDetail('feedback')}><span className="result-emblem"><Target size={22} /></span><span><strong>{last ? '最近练习 · ' + last.score + '% 正确率' : '从第一课，开始你的探索'}</strong><small>{state.player.xp} XP · {completed} / 5 章已完成 · 查看反馈</small></span><ChevronRight size={18} /></button>
        <button className="summary-open panel" onClick={() => setDetail('coach')}><span className="large-orb purple"><BookOpen size={23} /></span><span><strong>需要一点帮助？</strong><small>打开教学教练，解释概念与订单</small></span><ChevronRight size={18} /></button>
      </div>
      <Panel title="学习章节地图" icon={<Map className="blue" size={20} />} action={<Link className="text-link" to="/map">查看完整地图 <ChevronRight size={14} /></Link>} className="chapter-panel">
        <div className="chapter-path" data-tour="path">{state.courses.map((c, i) => <Link to={c.locked ? '/map' : '/learn/' + c.id} key={c.id} className={'chapter-node ' + (c.completed ? 'complete' : c.id === next.id ? 'current' : 'locked')}><span className="chapter-number">{c.completed ? <Check size={21} /> : i + 1}</span><span><strong>{c.short_title}</strong><small>{c.completed ? '已完成' : c.id === next.id ? '当前章节' : '未开始'}</small></span>{c.locked && <LockKeyhole size={13} />}</Link>)}</div>
      </Panel>
      <p className="home-note"><span />学习优先，而不是收益优先。每个小进步，都算数。</p>
    </div>
    <aside className="dashboard-aside">
      <Panel title="我的模拟账户" icon={<Layers className="blue" size={23} />} action={<span className="account-safety"><ShieldCheck size={19} /><span>仅使用虚拟资金<br />不进行真实交易</span></span>} className="account-panel">
        <p className="muted account-label" >虚拟总资产（人民币）</p><strong className="asset-total" data-tour="account">{formatMoney(account.total_assets)}</strong>
        <div className="account-metrics"><div><small>持仓市值</small><strong>{formatMoney(account.position_value)}</strong></div><div><small>可用资金</small><strong>{formatMoney(account.available_cash)}</strong></div></div>
        <button className="recent-order-open" onClick={() => setDetail('orders')}>最近订单<span>{account.orders[0] ? ({ pending: '待处理', filled: '已成交', cancelled: '已撤销', expired: '已到期' })[account.orders[0].status] : '暂无订单'}</span><ChevronRight size={14} /></button>
      </Panel>
      <Panel title="行情参考（示例）" icon={<ChartIcon />} action={<Link className="text-link" to="/simulate">查看更多 <ChevronRight size={13} /></Link>} className="market-panel">
        <div className="quote-title">{quote.name} <span>{quote.symbol}</span><span className="tiny">第 {account.day + 1} 教学日</span></div>
        <div className={'quote-price ' + (Number(quote.change) >= 0 ? 'up' : 'down')}><strong>{quote.price}</strong><span>{Number(quote.change) >= 0 ? '▲ +' : '▼ '}{quote.change}%</span></div>
        <Chart bars={account.bars} period={period} compact />
        <div className="segmented period-tabs" aria-label="行情周期">{[[1, '日K'], [5, '周K'], [20, '月K']].map(([value, text]) => <button key={value} aria-pressed={period === value} className={period === value ? 'selected' : ''} onClick={() => setPeriod(Number(value))}>{text}</button>)}</div>
        <p className="tiny muted chart-source">固定教学数据 · 非真实行情</p>
      </Panel>
      <button className="achievement-open panel" onClick={() => setDetail('achievements')}><Award className="amber-text" size={22} /><strong>我的成就</strong><span>{state.rewards.length} / 5 枚徽章</span><ChevronRight size={16} /></button>
    </aside>
    <Dialog open={detail === 'orders'} onOpenChange={open => !open && setDetail('')} title="最近一笔教学订单" description="完整订单、持仓与资金流水可在交易训练中查看。">        <div className="recent-order"><div className="section-line"><h3>最近一笔订单 <span>（模拟）</span></h3><Link className="text-link" to="/learn">查看全部 <ChevronRight size={13} /></Link></div>
          {account.orders[0] ? <div className="mini-order"><span className={'side-badge ' + account.orders[0].side}>{account.orders[0].side === 'buy' ? '买入' : '卖出'}</span><div><strong>{account.orders[0].name} <small>{account.orders[0].symbol}</small></strong><p>{account.orders[0].quantity} 股 · {account.orders[0].fill_price ? '成交价 ' + account.orders[0].fill_price : '委托价 ' + account.orders[0].limit_price}</p><small>{({ pending: '待处理', filled: '已成交', cancelled: '已撤销', expired: '已到期' })[account.orders[0].status]}</small></div></div> : <div className="no-order"><FileText size={22} /><div>还没有模拟订单<small>完成账户学习后，试着提交第一笔委托</small></div></div>}
        </div>
</Dialog>
    <Dialog open={detail === 'feedback'} onOpenChange={open => !open && setDetail('')} title="练习反馈" description="回顾独立练习的结果，再决定下一步。">        <Panel title="最近一次练习反馈" icon={<FileText className="blue" size={21} />} action={last ? <time className="tiny muted">{dateText(last.created_at)}</time> : <span className="tiny muted">等待你的第一次探索</span>} className="feedback-panel">
          <div className="feedback-summary"><span className={'result-emblem ' + (last && last.score < 100 ? 'amber' : '')}>{last ? <Check size={27} strokeWidth={3} /> : <Target size={28} />}</span><div><h3>{last ? last.score === 100 ? '独立练习，理解更进一步！' : '发现问题，也是进步' : '每一步，都是新起点'}</h3><p>{last ? '查看这次练习结果，把知识变成自己的能力。' : '从认识账户开始，完成你的第一项独立练习。'}</p></div></div>
          <div className="feedback-stats"><div><small>最近正确率</small><strong className="teal-text">{last ? last.score + '%' : '—'}</strong></div><div><small>获得学习经验</small><strong>{state.player.xp} <span>XP</span></strong></div><div><small>完成章节</small><strong><span className="teal-text">{completed}</span> / 5</strong></div></div>
          <div className="feedback-advice"><h4><CircleAlert className="amber-text" size={20} />{last ? '下一步可以这样做' : '开始前，记住这两件事'}</h4><ul>{last ? <><li>{last.feedback.find(f => !f.passed)?.explanation || '把本课的概念用自己的话解释一次，再进入下一关。'}</li><li>理解过程和原因，比一次模拟的盈亏更重要。</li></> : <><li>提交订单与完成成交是两个不同的状态。</li><li>所有账户都是模拟账户，学习不以盈利为通关条件。</li></>}</ul></div>
        </Panel>
</Dialog>
    <Dialog open={detail === 'coach'} onOpenChange={open => !open && setDetail('')} title="教学教练" description="解释知识与模拟规则，不提供股票预测。"><Coach lessonId={next.locked ? 'account' : next.id} /></Dialog>
    <Dialog open={detail === 'achievements'} onOpenChange={open => !open && setDetail('')} title="我的成就" description="每枚徽章来自你完成的一次独立练习。">      <Panel title="我的成就" icon={<Award className="blue" size={20} />} action={<Link className="text-link" to="/profile">查看更多 <ChevronRight size={13} /></Link>} className="achievements-panel">
        <div className="achievement-grid">{state.rewards.length ? state.rewards.slice(0, 2).map((r, i) => <Link to="/profile" className="achievement" key={r.lesson_id}><span className={'badge-medal ' + (i ? 'violet' : '')}><Award size={27} /></span><div><strong>{r.badge}</strong><small>独立练习完成</small><small>+{r.xp} XP</small></div></Link>) : <><div className="achievement unearned"><span className="badge-medal"><Award size={27} /></span><div><strong>新手探索者</strong><small>完成第一个章节</small><small>等待解锁</small></div></div><div className="achievement unearned"><span className="badge-medal violet"><ShieldCheck size={27} /></span><div><strong>完成第一笔</strong><small>理解订单与成交</small><small>等待解锁</small></div></div></>}
        </div>
      </Panel>
</Dialog>
  </motion.div>
}
function ChartIcon() { return <Gamepad2 className="blue" size={20} /> }
