import { useState } from 'react'
import { FileText, Layers } from 'lucide-react'
import { t, useLocale } from '../../i18n'
import type { Account, Bar, Order } from '../../lib/types'
import { formatMoney, useAction } from '../../lib/api'
import { ErrorNote } from '../../components/shared'
import { Button } from '../../components/ui/button'

export function AccountRecords({ account, readOnly = false, bars = account.bars }: { account: Account; readOnly?: boolean; bars?: Bar[] }) {
  useLocale()
  const [tab, setTab] = useState('orders')
  return <>
    <div className="record-tabs" role="tablist" aria-label={t('账户记录')}>
      {[["orders", t('订单记录')], ["positions", t('我的持仓')], ["ledger", t('资金流水')], ["prices", t('行情数据')]].map(([id, label]) =>
        <button role="tab" aria-selected={tab === id} className={tab === id ? 'active' : ''} key={id} onClick={() => setTab(id)}>{label}{id === 'orders' && <span>{account.orders.length}</span>}</button>)}
    </div>
    <div className="table-scroll" role="tabpanel">
      {tab === 'orders' && (account.orders.length ? <table><thead><tr><th>{t('教学股票')}</th><th>{t('方向 / 数量')}</th><th>{t('价格 / 费用')}</th><th>{t('状态与原因')}</th><th>{t('操作')}</th></tr></thead><tbody>{account.orders.map(order => <OrderRow key={order.id} order={order} mode={account.mode} readOnly={readOnly}/>)}</tbody></table> : <div className="empty-state small-empty"><FileText size={25}/><p>{t('本轮还没有订单记录。')}</p></div>)}
      {tab === 'positions' && (account.positions.length ? <table><thead><tr><th>{t('教学股票')}</th><th>{t('总持仓')}</th><th>{t('可卖')}</th><th>{t('冻结')}</th><th>{t('持仓成本（含买入费）')}</th></tr></thead><tbody>{account.positions.map(p => <tr key={p.symbol}><td>{p.name}</td><td>{p.quantity}{t('股')}</td><td>{p.sellable}{t('股')}</td><td>{p.frozen}{t('股')}</td><td>{formatMoney(p.cost)}{t('元')}</td></tr>)}</tbody></table> : <div className="empty-state small-empty"><Layers size={25}/><p>{t('本轮没有持仓。')}</p></div>)}
      {tab === 'ledger' && <table><thead><tr><th>{t('教学日')}</th><th>{t('来源')}</th><th>{t('资金变动（元）')}</th><th>{t('数量变动')}</th></tr></thead><tbody>{account.ledger.slice().reverse().map(l => <tr key={l.id}><td>D{l.day + 1}</td><td>{l.kind === 'initial' ? t('初始虚拟资金') : l.kind === 'buy' ? t('买入成交（含费）') : t('卖出成交（扣费）')}</td><td>{Number(l.cash_delta) > 0 ? '+' : ''}{formatMoney(l.cash_delta)}</td><td>{l.quantity_delta || '—'}</td></tr>)}</tbody></table>}
      {tab === 'prices' && <table><caption>{t('固定教学数据 · 截至本轮教学日')}</caption><thead><tr><th>{t('教学日')}</th><th>{t('开盘')}</th><th>{t('收盘')}</th><th>{t('最高')}</th><th>{t('最低')}</th><th>{t('成交量（股）')}</th></tr></thead><tbody>{bars.slice(-20).reverse().map(b => <tr key={b.day}><td>D{b.day + 1}</td><td>{b.open}</td><td>{b.close}</td><td>{b.high}</td><td>{b.low}</td><td>{b.volume.toLocaleString()}</td></tr>)}</tbody></table>}
    </div>
  </>
}

function OrderRow({ order: o, mode, readOnly }: { order: Order; mode: string; readOnly: boolean }) {
  useLocale()
  const cancel = useAction<Order, Record<string, never>>('/accounts/' + mode + '/orders/' + o.id + '/cancel')
  return <tr><td><strong>{o.name}</strong><small>{o.symbol} · D{o.created_day + 1}</small></td><td><span className={'side-badge ' + o.side}>{o.side === 'buy' ? t('买入') : t('卖出')}</span><small>{o.quantity}{t('股')}</small></td><td>{o.fill_price || o.limit_price}<small>{t('费用')}{formatMoney(o.fees)}</small></td><td className="reason-cell"><span className={'order-status ' + o.status}>{({ pending: t('待处理'), filled: t('已成交'), cancelled: t('已撤销'), expired: t('已到期') })[o.status]}</span><small>{o.reason}</small><ErrorNote error={cancel.error}/></td><td>{!readOnly && o.status === 'pending' ? <Button size="sm" variant="ghost" disabled={cancel.isPending} onClick={() => cancel.mutate({})}>{t('撤单')}</Button> : '—'}</td></tr>
}
