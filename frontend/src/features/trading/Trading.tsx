import { t, useLocale, i18n } from '../../i18n'
import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronRight, Clock3, FileText, Layers, ListOrdered, ShieldCheck, Wallet } from 'lucide-react';
import type { Account, Bar, Order, State } from '../../lib/types';
import { api, useAction, formatMoney } from '../../lib/api';
import { Panel, ErrorNote, Loading, PageHeader, Coach } from '../../components/shared';
import { Button } from '../../components/ui/button';
import { Dialog } from '../../components/ui/dialog';
import { Chart } from '../../components/Chart';
export function AccountStats({ account }: {
    account: Account;
}) {
    useLocale();
    return <div className="trading-stats">{[[Wallet, t("可用资金（虚拟）"), account.available_cash], [Layers, t("持仓市值（虚拟）"), account.position_value], [ShieldCheck, t("总资产（虚拟）"), account.total_assets], [Clock3, t("冻结资金"), account.frozen_cash]].map(([Icon, label, value]) => {
            const I = Icon as typeof Wallet;
            return <div key={String(label)}><span className="stat-icon"><I size={23}/></span><span><small>{String(label)}</small><strong>{formatMoney(String(value))}</strong></span></div>;
        })}</div>;
}
export function TradingSurface({ mode, compact = false }: {
    mode: 'tutorial' | 'free';
    compact?: boolean;
}) {
    useLocale();
    const query = useQuery({ queryKey: ['account', mode, i18n.language], placeholderData: (old, previous) => previous?.queryKey[1] === mode ? old : undefined, queryFn: () => api<Account>('/accounts/' + mode) });
    const account = query.data;
    const [period, setPeriod] = useState(1);
    const [symbol, setSymbol] = useState('SG001');
    const barsQuery = useQuery({ queryKey: ['bars', mode, symbol, account?.day, i18n.language], queryFn: () => api<Bar[]>('/accounts/' + mode + '/bars/' + symbol), enabled: symbol !== 'SG001' && !!account });
    const [side, setSide] = useState<'buy' | 'sell'>('buy');
    const [price, setPrice] = useState('21.50');
    const [quantity, setQuantity] = useState(100);
    const [tab, setTab] = useState('orders');
    const [recordsOpen, setRecordsOpen] = useState(false);
    const [notice, setNotice] = useState('');
    const submit = useAction<Order, {
        symbol: string;
        side: string;
        quantity: number;
        limit_price: string;
    }>('/accounts/' + mode + '/orders');
    const advance = useAction<Account, Record<string, never>>('/accounts/' + mode + '/advance');
    useEffect(() => {
        const quote = account?.quotes.find(q => q.symbol === symbol);
        if (quote)
            setPrice(quote.price);
    }, [symbol, account?.day]); // update default only when scenario changes
    if (query.isPending)
        return <Loading />;
    if (query.error || !account)
        return <ErrorNote error={query.error}/>;
    const quote = account.quotes.find(q => q.symbol === symbol)!;
    const busy = submit.isPending || advance.isPending;
    return <div className={'trading-surface ' + (compact ? 'compact' : '')}>
    <Panel className="trading-chart-panel">
      <div className="trading-chart-header"><div><span className="eyebrow">LEARNING SANDBOX</span><h2>{t("观察市场")}<span className="data-pill">{t("教学示例")}</span></h2></div><span className="muted tiny">{t("第 {{day}} 教学日 · 日线估算成交", { day: account.day + 1 })}</span></div>
      <div className="chart-toolbar"><div className="stock-select"><label htmlFor={'symbol-' + mode} className="sr-only">{t("教学股票")}</label><select id={'symbol-' + mode} value={symbol} onChange={e => setSymbol(e.target.value)}>{account.quotes.map(q => <option key={q.symbol} value={q.symbol}>{q.name} · {q.symbol}</option>)}</select><strong className={Number(quote.change) >= 0 ? 'up' : 'down'}>{quote.price} <small>{Number(quote.change) >= 0 ? '+' : ''}{quote.change}%</small></strong></div><div className="segmented">{[[1, t("日线")], [5, t("周线")], [20, t("月线")]].map(([p, title]) => <button key={p} aria-pressed={period === p} className={period === p ? 'selected' : ''} onClick={() => setPeriod(Number(p))}>{title}</button>)}</div></div>
      {symbol === 'SG001' ? <Chart bars={account.bars} period={period}/> : barsQuery.isPending ? <Loading /> : barsQuery.error ? <ErrorNote error={barsQuery.error}/> : <Chart bars={barsQuery.data} period={period}/>}
      <div className="chart-caption"><span><i className="up-dot"/>{t("上涨")}<i className="down-dot"/>{t("下跌")}</span><span>{t("仅展示截至第")}{account.day + 1}{t("日的数据 · 非真实行情")}</span></div>
    </Panel>
    <Panel className="order-entry">
      <form onSubmit={e => { e.preventDefault(); setNotice(''); submit.mutate({ symbol, side, quantity, limit_price: price }, { onSuccess: o => { setNotice(o.reason); setTab('orders'); setRecordsOpen(true); } }); }}>
        <div className="side-tabs" aria-label={t("买卖方向")}><button type="button" className={side === 'buy' ? 'buy selected' : ''} aria-pressed={side === 'buy'} onClick={() => setSide('buy')}>{t("买入")}</button><button type="button" className={side === 'sell' ? 'sell selected' : ''} aria-pressed={side === 'sell'} onClick={() => setSide('sell')}>{t("卖出")}</button></div>
        <label className="order-field">{t("委托价格（元）")}<input aria-label={t("委托价格")} type="number" step="0.01" min="0.01" max="999999" value={price} onChange={e => setPrice(e.target.value)} required/></label>
        <label className="order-field">{t("数量（股）")}<input aria-label={t("委托数量")} type="number" step="100" min="100" max="1000000" value={quantity} onChange={e => setQuantity(Number(e.target.value))} required/></label>
        <Button type="submit" disabled={busy || !price || !quantity}>{t("提交模拟订单")}<ChevronRight size={17}/></Button>
      </form>
      <p className="tiny muted">{t("限价委托 · 100 股整数倍 · 订单在下一教学日处理")}</p><ErrorNote error={submit.error}/>{notice && <p className="success-note" role="status">{notice}</p>}
    </Panel>
    <AccountStats account={account}/>
    <Panel title={t("账户与交易记录")} icon={<ListOrdered className="blue" size={19}/>} action={<Button size="sm" variant="secondary" disabled={busy || account.day >= 59} onClick={() => { setNotice(''); advance.mutate({}, { onSuccess: () => { setNotice(t("已推进下一教学日。请阅读订单结果与费用，检查可卖数量。")); setRecordsOpen(true); } }); }}>{advance.isPending ? t("结算中…") : t("下一教学日")}<ChevronRight size={15}/></Button>} className="records-panel">
      <ErrorNote error={advance.error}/>
      <div className="record-summary"><span>{account.orders.filter(o => o.status === 'pending').length}{t("笔待处理 ·")}{account.positions.length}{t("只持仓")}</span><Button size="sm" variant="ghost" onClick={() => setRecordsOpen(true)}>{t("查看订单 / 持仓 / 流水")}</Button></div><Dialog wide open={recordsOpen} onOpenChange={setRecordsOpen} title={t("账户与交易记录")} description={t("第 ") + (account.day + 1) + t(" 教学日 · ") + (mode === 'tutorial' ? t("教学账户") : t("自由模拟账户"))}><div className="record-tabs" role="tablist" aria-label={t("账户记录")}>{[['orders', t("订单记录")], ['positions', t("我的持仓")], ['ledger', t("资金流水")], ['prices', t("行情数据")]].map(([id, text]) => <button role="tab" aria-selected={tab === id} className={tab === id ? 'active' : ''} key={id} onClick={() => setTab(id)}>{text}{id === 'orders' && <span>{account.orders.length}</span>}</button>)}</div>
      <div className="table-scroll" role="tabpanel">
        {tab === 'orders' && (account.orders.length ? <table><thead><tr><th>{t("教学股票")}</th><th>{t("方向 / 数量")}</th><th>{t("价格 / 费用")}</th><th>{t("状态与原因")}</th><th>{t("操作")}</th></tr></thead><tbody>{account.orders.map(o => <OrderRow key={o.id} order={o} mode={mode}/>)}</tbody></table> : <div className="empty-state small-empty"><FileText size={25}/><p>{t("还没有订单，提交一次委托，看看它如何被处理。")}</p></div>)}
        {tab === 'positions' && (account.positions.length ? <table><thead><tr><th>{t("教学股票")}</th><th>{t("总持仓")}</th><th>{t("可卖")}</th><th>{t("冻结")}</th><th>{t("持仓成本（含买入费）")}</th></tr></thead><tbody>{account.positions.map(p => <tr key={p.symbol}><td>{p.name}</td><td>{p.quantity}{t("股")}</td><td>{p.sellable}{t("股")}</td><td>{p.frozen}{t("股")}</td><td>{formatMoney(p.cost)}{t("元")}</td></tr>)}</tbody></table> : <div className="empty-state small-empty"><Layers size={25}/><p>{t("成交后，持仓会出现在这里。委托尚未成交时不会增加持仓。")}</p></div>)}
        {tab === 'ledger' && <table><thead><tr><th>{t("教学日")}</th><th>{t("来源")}</th><th>{t("资金变动（元）")}</th><th>{t("数量变动")}</th></tr></thead><tbody>{account.ledger.slice().reverse().map(l => <tr key={l.id}><td>D{l.day + 1}</td><td>{l.kind === 'initial' ? t("初始虚拟资金") : l.kind === 'buy' ? t("买入成交（含费）") : t("卖出成交（扣费）")}</td><td>{Number(l.cash_delta) > 0 ? '+' : ''}{formatMoney(l.cash_delta)}</td><td>{l.quantity_delta || '—'}</td></tr>)}</tbody></table>}
        {tab === 'prices' && <table><caption>{quote.name}{t("· 固定教学数据 · 截至当前教学日")}</caption><thead><tr><th>{t("教学日")}</th><th>{t("开盘")}</th><th>{t("收盘")}</th><th>{t("最高")}</th><th>{t("最低")}</th><th>{t("成交量（股）")}</th></tr></thead><tbody>{(symbol === 'SG001' ? account.bars : barsQuery.data || []).slice(-20).reverse().map(b => <tr key={b.day}><td>D{b.day + 1}</td><td>{b.open}</td><td>{b.close}</td><td>{b.high}</td><td>{b.low}</td><td>{b.volume.toLocaleString()}</td></tr>)}</tbody></table>}
      </div></Dialog>
    </Panel>
  </div>;
}
function OrderRow({ order: o, mode }: {
    order: Order;
    mode: string;
}) {
    useLocale();
    const cancel = useAction<Order, Record<string, never>>('/accounts/' + mode + '/orders/' + o.id + '/cancel');
    return <tr><td><strong>{o.name}</strong><small>{o.symbol} · D{o.created_day + 1}</small></td><td><span className={'side-badge ' + o.side}>{o.side === 'buy' ? t("买入") : t("卖出")}</span><small>{o.quantity}{t("股")}</small></td><td>{o.fill_price || o.limit_price}<small>{t("费用")}{formatMoney(o.fees)}</small></td><td className="reason-cell"><span className={'order-status ' + o.status}>{({ pending: t("待处理"), filled: t("已成交"), cancelled: t("已撤销"), expired: t("已到期") })[o.status]}</span><small>{o.reason}</small><ErrorNote error={cancel.error}/></td><td>{o.status === 'pending' ? <Button size="sm" variant="ghost" disabled={cancel.isPending} onClick={() => cancel.mutate({})}>{t("撤单")}</Button> : '—'}</td></tr>;
}
export default function Trading({ state }: {
    state: State;
}) {
    useLocale();
    const [coachOpen, setCoachOpen] = useState(false);
    const next = state.courses.find(c => !c.completed && !c.locked);
    return <div><PageHeader eyebrow={t("PRACTICE / 自由模拟")} title={t("把所学，放进一次练习")} description={t("独立的虚拟账户，自主设定价格、观察订单、记录思考。")}/>
    <div className="mission-layout"><TradingSurface mode="free"/><aside className="mission-aside"><Panel title={t("本次练习目标")} icon={<ShieldCheck className="amber-text"/>}><div className="objective-copy"><span className="eyebrow">FREE PRACTICE</span><h3>{t("在每一次决策前，多想一步")}</h3><p>{t("这里的账户与课程账户分开。自由模拟不会因为下单次数或收益增加学习经验。")}</p><ul><li>{t("确认可用资金和可卖数量")}</li><li>{t("明确价格、数量与仓位")}</li><li>{t("查看处理结果和费用")}</li><li>{t("回顾结果与原先计划")}</li></ul></div></Panel><Button variant="secondary" onClick={() => setCoachOpen(true)}>{t("请教教学教练")}</Button><Dialog open={coachOpen} onOpenChange={setCoachOpen} title={t("教学教练")} description={t("理解本次练习的规则。")}><Coach lessonId={next?.id || 'account'}/></Dialog></aside></div>
  </div>;
}
