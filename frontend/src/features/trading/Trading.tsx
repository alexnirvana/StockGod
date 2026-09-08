import { t, useLocale, i18n } from '../../i18n'
import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronRight, Clock3, Layers, ListOrdered, ShieldCheck, Wallet } from 'lucide-react';
import type { Account, AccountContext, Bar, Order, State } from '../../lib/types';
import { api, useAction, formatMoney } from '../../lib/api';
import { Panel, ErrorNote, Loading, PageHeader, Coach } from '../../components/shared';
import { Button } from '../../components/ui/button';
import { Dialog } from '../../components/ui/dialog';
import { Chart } from '../../components/Chart';
import { AccountRecords } from './AccountRecords';
import { PracticeRounds } from './PracticeRounds';
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
    const barsQuery = useQuery({ queryKey: ['bars', mode, account?.id, symbol, account?.day, i18n.language], queryFn: () => api<Bar[]>('/accounts/' + mode + '/bars/' + symbol), enabled: symbol !== 'SG001' && !!account });
    const [side, setSide] = useState<'buy' | 'sell'>('buy');
    const [price, setPrice] = useState('21.50');
    const [quantity, setQuantity] = useState(100);
    const [recordsOpen, setRecordsOpen] = useState(false);
    const [notice, setNotice] = useState('');
    const submit = useAction<Order, {
        symbol: string;
        side: string;
        quantity: number;
        limit_price: string;
        expected_account_id: string;
        expected_day: number;
    }>('/accounts/' + mode + '/orders');
    const advance = useAction<Account, AccountContext>('/accounts/' + mode + '/advance');
    useEffect(() => {
        const quote = account?.quotes.find(q => q.symbol === symbol);
        if (quote)
            setPrice(quote.price);
    }, [symbol, account?.id, account?.day]); // update default only when scenario changes
    useEffect(() => { setNotice(''); setRecordsOpen(false); submit.reset(); advance.reset(); }, [account?.id]);
    if (query.isPending)
        return <Loading />;
    if (query.error || !account)
        return <ErrorNote error={query.error}/>;
    const quote = account.quotes.find(q => q.symbol === symbol)!;
    const busy = submit.isPending || advance.isPending;
    return <div className={'trading-surface ' + (compact ? 'compact' : '')}>
    <Panel className="trading-chart-panel">
      <div className="trading-chart-header"><div><span className="eyebrow">{mode === 'free' ? t("第 {{round}} 轮 · 自由模拟", { round: account.round_number }) : 'LEARNING SANDBOX'}</span><h2>{t("观察市场")}<span className="data-pill">{t("教学示例")}</span></h2></div><span className="muted tiny">{mode === 'free' ? t("第 {{round}} 轮 · 第 {{day}} 教学日", { round: account.round_number, day: account.day + 1 }) : t("第 {{day}} 教学日 · 日线估算成交", { day: account.day + 1 })}</span></div>
      <div className="chart-toolbar"><div className="stock-select"><label htmlFor={'symbol-' + mode} className="sr-only">{t("教学股票")}</label><select id={'symbol-' + mode} value={symbol} onChange={e => setSymbol(e.target.value)}>{account.quotes.map(q => <option key={q.symbol} value={q.symbol}>{q.name} · {q.symbol}</option>)}</select><strong className={Number(quote.change) >= 0 ? 'up' : 'down'}>{quote.price} <small>{Number(quote.change) >= 0 ? '+' : ''}{quote.change}%</small></strong></div><div className="segmented">{[[1, t("日线")], [5, t("周线")], [20, t("月线")]].map(([p, title]) => <button key={p} aria-pressed={period === p} className={period === p ? 'selected' : ''} onClick={() => setPeriod(Number(p))}>{title}</button>)}</div></div>
      {symbol === 'SG001' ? <Chart bars={account.bars} period={period}/> : barsQuery.isPending ? <Loading /> : barsQuery.error ? <ErrorNote error={barsQuery.error}/> : <Chart bars={barsQuery.data} period={period}/>}
      <div className="chart-caption"><span><i className="up-dot"/>{t("上涨")}<i className="down-dot"/>{t("下跌")}</span><span>{t("仅展示截至第")}{account.day + 1}{t("日的数据 · 非真实行情")}</span></div>
    </Panel>
    <Panel className="order-entry">
      <form onSubmit={e => { e.preventDefault(); setNotice(''); submit.mutate({ symbol, side, quantity, limit_price: price, expected_account_id: account.id, expected_day: account.day }, { onSuccess: o => { setNotice(o.reason); setRecordsOpen(true); } }); }}>
        <div className="side-tabs" aria-label={t("买卖方向")}><button type="button" className={side === 'buy' ? 'buy selected' : ''} aria-pressed={side === 'buy'} onClick={() => setSide('buy')}>{t("买入")}</button><button type="button" className={side === 'sell' ? 'sell selected' : ''} aria-pressed={side === 'sell'} onClick={() => setSide('sell')}>{t("卖出")}</button></div>
        <label className="order-field">{t("委托价格（元）")}<input aria-label={t("委托价格")} type="number" step="0.01" min="0.01" max="999999" value={price} onChange={e => setPrice(e.target.value)} required/></label>
        <label className="order-field">{t("数量（股）")}<input aria-label={t("委托数量")} type="number" step="100" min="100" max="1000000" value={quantity} onChange={e => setQuantity(Number(e.target.value))} required/></label>
        <Button type="submit" disabled={busy || account.day >= 59 || !price || !quantity}>{t("提交模拟订单")}<ChevronRight size={17}/></Button>
      </form>
      <p className="tiny muted">{t("限价委托 · 100 股整数倍 · 订单在下一教学日处理")}</p><ErrorNote error={submit.error}/>{notice && <p className="success-note" role="status">{notice}</p>}
    </Panel>
    <AccountStats account={account}/>
    <Panel title={t("账户与交易记录")} icon={<ListOrdered className="blue" size={19}/>} action={<Button size="sm" variant="secondary" disabled={busy || account.day >= 59} onClick={() => { setNotice(''); advance.mutate({ expected_account_id: account.id, expected_day: account.day }, { onSuccess: () => { setNotice(t("已推进下一教学日。请阅读订单结果与费用，检查可卖数量。")); setRecordsOpen(true); } }); }}>{advance.isPending ? t("结算中…") : t("下一教学日")}<ChevronRight size={15}/></Button>} className="records-panel">
      <ErrorNote error={advance.error}/>
      <div className="record-summary"><span>{account.orders.filter(o => o.status === 'pending').length}{t("笔待处理 ·")}{account.positions.length}{t("只持仓")}</span><Button size="sm" variant="ghost" onClick={() => setRecordsOpen(true)}>{t("查看订单 / 持仓 / 流水")}</Button></div><Dialog wide open={recordsOpen} onOpenChange={setRecordsOpen} title={t("账户与交易记录")} description={t("第 ") + (account.day + 1) + t(" 教学日 · ") + (mode === 'tutorial' ? t("教学账户") : t("自由模拟账户"))}><AccountRecords key={account.id + String(recordsOpen)} account={account} bars={symbol === 'SG001' ? account.bars : barsQuery.data || []}/></Dialog>
    </Panel>
  </div>;
}
export default function Trading({ state }: {
    state: State;
}) {
    useLocale();
    const [coachOpen, setCoachOpen] = useState(false);
    const next = state.courses.find(c => !c.completed && !c.locked);
    return <div><PageHeader eyebrow={t("PRACTICE / 自由模拟")} title={t("把所学，放进一次练习")} description={t("独立的虚拟账户，自主设定价格、观察订单、记录思考。")}/>
    <div className="mission-layout"><TradingSurface mode="free"/><aside className="mission-aside"><Panel title={t("本次练习目标")} icon={<ShieldCheck className="amber-text"/>}><div className="objective-copy"><span className="eyebrow">FREE PRACTICE</span><h3>{t("在每一次决策前，多想一步")}</h3><p>{t("这里的账户与课程账户分开。自由模拟不会因为下单次数或收益增加学习经验。")}</p><ul><li>{t("确认可用资金和可卖数量")}</li><li>{t("明确价格、数量与仓位")}</li><li>{t("查看处理结果和费用")}</li><li>{t("回顾结果与原先计划")}</li></ul></div></Panel><PracticeRounds/><Button variant="secondary" onClick={() => setCoachOpen(true)}>{t("请教教学教练")}</Button><Dialog open={coachOpen} onOpenChange={setCoachOpen} title={t("教学教练")} description={t("理解本次练习的规则。")}><Coach lessonId={next?.id || 'account'}/></Dialog></aside></div>
  </div>;
}
