import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronRight, Clock3, FileText, Layers, ListOrdered, ShieldCheck, Wallet } from 'lucide-react'
import type { Account, Bar, Order, State } from '../../lib/types'
import { api, useAction, formatMoney } from '../../lib/api'
import { Panel, ErrorNote, Loading, PageHeader, Coach } from '../../components/shared'
import { Button } from '../../components/ui/button'
import { Dialog } from '../../components/ui/dialog'
import { Chart } from '../../components/Chart'

const states = { pending: '待处理', filled: '已成交', cancelled: '已撤销', expired: '已到期' }
export function AccountStats({ account }: { account: Account }) {
  return <div className="trading-stats">{[[Wallet, '可用资金（虚拟）', account.available_cash], [Layers, '持仓市值（虚拟）', account.position_value], [ShieldCheck, '总资产（虚拟）', account.total_assets], [Clock3, '冻结资金', account.frozen_cash]].map(([Icon, label, value]) => {
    const I = Icon as typeof Wallet
    return <div key={String(label)}><span className="stat-icon"><I size={23} /></span><span><small>{String(label)}</small><strong>{formatMoney(String(value))}</strong></span></div>
  })}</div>
}
export function TradingSurface({ mode, compact = false }: { mode: 'tutorial' | 'free'; compact?: boolean }) {
  const query = useQuery({ queryKey: ['account', mode], queryFn: () => api<Account>('/accounts/' + mode) })
  const account = query.data
  const [period, setPeriod] = useState(1)
  const [symbol, setSymbol] = useState('SG001')
  const barsQuery = useQuery({ queryKey: ['bars', mode, symbol, account?.day], queryFn: () => api<Bar[]>('/accounts/' + mode + '/bars/' + symbol), enabled: symbol !== 'SG001' && !!account })
  const [side, setSide] = useState<'buy' | 'sell'>('buy')
  const [price, setPrice] = useState('21.50')
  const [quantity, setQuantity] = useState(100)
  const [tab, setTab] = useState('orders')
  const [recordsOpen, setRecordsOpen] = useState(false)
  const [notice, setNotice] = useState('')
  const submit = useAction<Order, { symbol: string; side: string; quantity: number; limit_price: string }>('/accounts/' + mode + '/orders')
  const advance = useAction<Account, Record<string, never>>('/accounts/' + mode + '/advance')
  useEffect(() => {
    const quote = account?.quotes.find(q => q.symbol === symbol)
    if (quote) setPrice(quote.price)
  }, [symbol, account?.day]) // update default only when scenario changes
  if (query.isPending) return <Loading />
  if (query.error || !account) return <ErrorNote error={query.error} />
  const quote = account.quotes.find(q => q.symbol === symbol)!
  const busy = submit.isPending || advance.isPending
  return <div className={'trading-surface ' + (compact ? 'compact' : '')}>
    <Panel className="trading-chart-panel">
      <div className="trading-chart-header"><div><span className="eyebrow">LEARNING SANDBOX</span><h2>观察市场 <span className="data-pill">教学示例</span></h2></div><span className="muted tiny">第 {account.day + 1} 教学日 · 日线估算成交</span></div>
      <div className="chart-toolbar"><div className="stock-select"><label htmlFor={'symbol-' + mode} className="sr-only">教学股票</label><select id={'symbol-' + mode} value={symbol} onChange={e => setSymbol(e.target.value)}>{account.quotes.map(q => <option key={q.symbol} value={q.symbol}>{q.name} · {q.symbol}</option>)}</select><strong className={Number(quote.change) >= 0 ? 'up' : 'down'}>{quote.price} <small>{Number(quote.change) >= 0 ? '+' : ''}{quote.change}%</small></strong></div><div className="segmented">{[[1, '日线'], [5, '周线'], [20, '月线']].map(([p, title]) => <button key={p} aria-pressed={period === p} className={period === p ? 'selected' : ''} onClick={() => setPeriod(Number(p))}>{title}</button>)}</div></div>
      {symbol === 'SG001' ? <Chart bars={account.bars} period={period} /> : barsQuery.isPending ? <Loading /> : barsQuery.error ? <ErrorNote error={barsQuery.error} /> : <Chart bars={barsQuery.data} period={period} />}
      <div className="chart-caption"><span><i className="up-dot" />上涨 <i className="down-dot" />下跌</span><span>仅展示截至第 {account.day + 1} 日的数据 · 非真实行情</span></div>
    </Panel>
    <Panel className="order-entry">
      <form onSubmit={e => { e.preventDefault(); setNotice(''); submit.mutate({ symbol, side, quantity, limit_price: price }, { onSuccess: o => { setNotice(o.reason); setTab('orders'); setRecordsOpen(true) } }) }}>
        <div className="side-tabs" aria-label="买卖方向"><button type="button" className={side === 'buy' ? 'buy selected' : ''} aria-pressed={side === 'buy'} onClick={() => setSide('buy')}>买入</button><button type="button" className={side === 'sell' ? 'sell selected' : ''} aria-pressed={side === 'sell'} onClick={() => setSide('sell')}>卖出</button></div>
        <label className="order-field">委托价格（元）<input aria-label="委托价格" type="number" step="0.01" min="0.01" max="999999" value={price} onChange={e => setPrice(e.target.value)} required /></label>
        <label className="order-field">数量（股）<input aria-label="委托数量" type="number" step="100" min="100" max="1000000" value={quantity} onChange={e => setQuantity(Number(e.target.value))} required /></label>
        <Button type="submit" disabled={busy || !price || !quantity}>提交模拟订单 <ChevronRight size={17} /></Button>
      </form>
      <p className="tiny muted">限价委托 · 100 股整数倍 · 订单在下一教学日处理</p><ErrorNote error={submit.error} />{notice && <p className="success-note" role="status">{notice}</p>}
    </Panel>
    <AccountStats account={account} />
    <Panel title="账户与交易记录" icon={<ListOrdered className="blue" size={19} />} action={<Button size="sm" variant="secondary" disabled={busy || account.day >= 59} onClick={() => { setNotice(''); advance.mutate({}, { onSuccess: () => { setNotice('已推进下一教学日。请阅读订单结果与费用，检查可卖数量。'); setRecordsOpen(true) } }) }}>{advance.isPending ? '结算中…' : '下一教学日'}<ChevronRight size={15} /></Button>} className="records-panel">
      <ErrorNote error={advance.error} />
      <div className="record-summary"><span>{account.orders.filter(o => o.status === 'pending').length} 笔待处理 · {account.positions.length} 只持仓</span><Button size="sm" variant="ghost" onClick={() => setRecordsOpen(true)}>查看订单 / 持仓 / 流水</Button></div><Dialog wide open={recordsOpen} onOpenChange={setRecordsOpen} title="账户与交易记录" description={'第 ' + (account.day + 1) + ' 教学日 · ' + (mode === 'tutorial' ? '教学账户' : '自由模拟账户')}><div className="record-tabs" role="tablist" aria-label="账户记录">{[['orders', '订单记录'], ['positions', '我的持仓'], ['ledger', '资金流水'], ['prices', '行情数据']].map(([id, text]) => <button role="tab" aria-selected={tab === id} className={tab === id ? 'active' : ''} key={id} onClick={() => setTab(id)}>{text}{id === 'orders' && <span>{account.orders.length}</span>}</button>)}</div>
      <div className="table-scroll" role="tabpanel">
        {tab === 'orders' && (account.orders.length ? <table><thead><tr><th>教学股票</th><th>方向 / 数量</th><th>价格 / 费用</th><th>状态与原因</th><th>操作</th></tr></thead><tbody>{account.orders.map(o => <OrderRow key={o.id} order={o} mode={mode} />)}</tbody></table> : <div className="empty-state small-empty"><FileText size={25} /><p>还没有订单，提交一次委托，看看它如何被处理。</p></div>)}
        {tab === 'positions' && (account.positions.length ? <table><thead><tr><th>教学股票</th><th>总持仓</th><th>可卖</th><th>冻结</th><th>持仓成本（含买入费）</th></tr></thead><tbody>{account.positions.map(p => <tr key={p.symbol}><td>{p.name}</td><td>{p.quantity} 股</td><td>{p.sellable} 股</td><td>{p.frozen} 股</td><td>{formatMoney(p.cost)} 元</td></tr>)}</tbody></table> : <div className="empty-state small-empty"><Layers size={25} /><p>成交后，持仓会出现在这里。委托尚未成交时不会增加持仓。</p></div>)}
        {tab === 'ledger' && <table><thead><tr><th>教学日</th><th>来源</th><th>资金变动（元）</th><th>数量变动</th></tr></thead><tbody>{account.ledger.slice().reverse().map(l => <tr key={l.id}><td>D{l.day + 1}</td><td>{l.kind === 'initial' ? '初始虚拟资金' : l.kind === 'buy' ? '买入成交（含费）' : '卖出成交（扣费）'}</td><td>{Number(l.cash_delta) > 0 ? '+' : ''}{formatMoney(l.cash_delta)}</td><td>{l.quantity_delta || '—'}</td></tr>)}</tbody></table>}
        {tab === 'prices' && <table><caption>{quote.name} · 固定教学数据 · 截至当前教学日</caption><thead><tr><th>教学日</th><th>开盘</th><th>收盘</th><th>最高</th><th>最低</th><th>成交量（股）</th></tr></thead><tbody>{(symbol === 'SG001' ? account.bars : barsQuery.data || []).slice(-20).reverse().map(b => <tr key={b.day}><td>D{b.day + 1}</td><td>{b.open}</td><td>{b.close}</td><td>{b.high}</td><td>{b.low}</td><td>{b.volume.toLocaleString()}</td></tr>)}</tbody></table>}
      </div></Dialog>
    </Panel>
  </div>
}
function OrderRow({ order: o, mode }: { order: Order; mode: string }) {
  const cancel = useAction<Order, Record<string, never>>('/accounts/' + mode + '/orders/' + o.id + '/cancel')
  return <tr><td><strong>{o.name}</strong><small>{o.symbol} · D{o.created_day + 1}</small></td><td><span className={'side-badge ' + o.side}>{o.side === 'buy' ? '买入' : '卖出'}</span><small>{o.quantity} 股</small></td><td>{o.fill_price || o.limit_price}<small>费用 {formatMoney(o.fees)}</small></td><td className="reason-cell"><span className={'order-status ' + o.status}>{states[o.status]}</span><small>{o.reason}</small><ErrorNote error={cancel.error} /></td><td>{o.status === 'pending' ? <Button size="sm" variant="ghost" disabled={cancel.isPending} onClick={() => cancel.mutate({})}>撤单</Button> : '—'}</td></tr>
}
export default function Trading({ state }: { state: State }) {
  const [coachOpen, setCoachOpen] = useState(false)
  const next = state.courses.find(c => !c.completed && !c.locked)
  return <div><PageHeader eyebrow="PRACTICE / 自由模拟" title="把所学，放进一次练习" description="独立的虚拟账户，自主设定价格、观察订单、记录思考。" />
    <div className="mission-layout"><TradingSurface mode="free" /><aside className="mission-aside"><Panel title="本次练习目标" icon={<ShieldCheck className="amber-text" />}><div className="objective-copy"><span className="eyebrow">FREE PRACTICE</span><h3>在每一次决策前，多想一步</h3><p>这里的账户与课程账户分开。自由模拟不会因为下单次数或收益增加学习经验。</p><ul><li>确认可用资金和可卖数量</li><li>明确价格、数量与仓位</li><li>查看处理结果和费用</li><li>回顾结果与原先计划</li></ul></div></Panel><Button variant="secondary" onClick={() => setCoachOpen(true)}>请教教学教练</Button><Dialog open={coachOpen} onOpenChange={setCoachOpen} title="教学教练" description="理解本次练习的规则。"><Coach lessonId={next?.id || 'account'} /></Dialog></aside></div>
  </div>
}
