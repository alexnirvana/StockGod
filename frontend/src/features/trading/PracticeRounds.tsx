import { useState } from 'react'
import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { History, RotateCcw, FileText, ArrowLeft } from 'lucide-react'
import { t, useLocale, i18n } from '../../i18n'
import { api, dateText, formatMoney, useAction } from '../../lib/api'
import type { Account, AccountContext, PracticeRound, PracticeReport } from '../../lib/types'
import { ErrorNote, Loading } from '../../components/shared'
import { Button } from '../../components/ui/button'
import { Dialog } from '../../components/ui/dialog'
import { AccountRecords } from './AccountRecords'
import { ReflectionForm } from '../learning/Learning'

export function PracticeRounds() {
  useLocale()
  const [dialog, setDialog] = useState<'history' | 'new' | 'reflection' | ''>('')
  const account = useQuery({ queryKey: ['account', 'free', i18n.language], queryFn: () => api<Account>('/accounts/free') })
  // Freeze the context the user reviewed; a background refresh must not silently change it.
  const [reviewed, setReviewed] = useState<Account | null>(null)
  const action = useAction<Account, AccountContext>('/practice/rounds')
  const pending = reviewed?.orders.some(o => o.status === 'pending')
  function open(kind: typeof dialog) {
    setReviewed(account.data || null)
    action.reset()
    setDialog(kind)
  }
  return <>
    <div className="practice-actions">
      <Button variant="secondary" onClick={() => open('history')}><History size={16}/>{t('练习轮次')}</Button>
      <Button variant="secondary" disabled={!account.data} onClick={() => open('new')}><RotateCcw size={16}/>{t('新一轮练习')}</Button>
      <Button variant="ghost" disabled={!account.data} onClick={() => open('reflection')}><FileText size={16}/>{t('保存本轮复盘')}</Button>
    </div>
    <ErrorNote error={account.error}/>
    <Dialog wide open={dialog === 'history'} onOpenChange={open => !open && setDialog('')} title={t('练习轮次')} description={t('每轮独立保存，归档后可回看订单、持仓、流水和复盘。')}>
      {dialog === 'history' && <RoundHistory/>}
    </Dialog>
    <Dialog open={dialog === 'new'} onOpenChange={open => !open && !action.isPending && setDialog('')} title={t('开始新一轮练习')} description={t('当前轮次会归档，新一轮从第 20 教学日和 100,000 元虚拟资金开始。')}>
      {reviewed && <div className="round-confirm">
        <div className="round-summary"><strong>{t('第 {{round}} 轮', { round: reviewed.round_number })}</strong><span>{t('第 {{day}} 教学日', { day: reviewed.day + 1 })}</span><span>{t('总资产（虚拟）')} ¥{formatMoney(reviewed.total_assets)}</span></div>
        <p>{t('旧轮次的持仓按归档当日保留，不自动卖出；之后只能查看。新轮次使用相同的固定教学场景。')}</p>
        <p className="muted">{t('教学账户、课程进度和经验保持独立。')}</p>
        {pending && <p className="amber-text" role="status">{t('本轮还有待处理订单，请先撤单或推进教学日完成处理。')}</p>}
        <ErrorNote error={action.error}/>
        <div className="round-buttons"><Button variant="secondary" disabled={action.isPending} onClick={() => setDialog('')}>{t('返回当前练习')}</Button><Button disabled={action.isPending || pending} onClick={() => action.mutate({ expected_account_id: reviewed.id, expected_day: reviewed.day }, { onSuccess: () => setDialog('') })}>{action.isPending ? t('正在创建…') : t('归档并开始新一轮')}</Button></div>
      </div>}
    </Dialog>
    <Dialog open={dialog === 'reflection'} onOpenChange={open => !open && setDialog('')} title={t('保存本轮复盘')} description={t('复盘会关联到打开弹窗时的练习轮次。')}>
      {dialog === 'reflection' && reviewed && <ReflectionForm key={reviewed.id} mode="free" context={{ expected_account_id: reviewed.id, expected_day: reviewed.day }}/>}
    </Dialog>
  </>
}

function RoundHistory() {
  const [selected, setSelected] = useState('')
  const history = useInfiniteQuery({
    queryKey: ['practice-rounds', i18n.language], initialPageParam: null as number | null,
    queryFn: ({ pageParam }) => api<{ items: PracticeRound[]; next_before: number | null }>('/practice/rounds?limit=10' + (pageParam === null ? '' : '&before=' + pageParam)),
    getNextPageParam: page => page.next_before ?? undefined,
  })
  if (selected) return <><Button size="sm" variant="ghost" onClick={() => setSelected('')}><ArrowLeft size={16}/>{t('返回轮次列表')}</Button><RoundReport id={selected}/></>
  return <div className="round-history">
    {history.isPending ? <Loading/> : <ErrorNote error={history.error}/>}
    {history.data?.pages.flatMap(page => page.items).map(round => <article key={round.id}>
      <div><strong>{t('第 {{round}} 轮', { round: round.round_number })}</strong><span className="data-pill">{round.archived_at ? t('已归档') : t('当前练习')}</span><p>{t('第 {{day}} 教学日', { day: round.day + 1 })}{round.archived_at && ' · ' + dateText(round.archived_at)}</p><small>{round.data_version}</small></div>
      <Button variant="secondary" size="sm" onClick={() => setSelected(round.id)}>{t('查看轮次记录')}</Button>
    </article>)}
    {history.hasNextPage && <Button variant="ghost" disabled={history.isFetchingNextPage} onClick={() => history.fetchNextPage()}>{t('加载更早轮次')}</Button>}
  </div>
}

function RoundReport({ id }: { id: string }) {
  const report = useQuery({ queryKey: ['practice-report', id, i18n.language], queryFn: () => api<PracticeReport>('/practice/rounds/' + id) })
  if (report.isPending) return <Loading/>
  if (!report.data) return <ErrorNote error={report.error}/>
  const account = report.data
  return <div className="round-report">
    <h3>{t('第 {{round}} 轮', { round: account.round_number })} · {account.archived_at ? t('已归档') : t('当前练习')}</h3>
    <p className="muted">{t('截至第 {{day}} 教学日 · 教学示例', { day: account.day + 1 })}</p>
    <div className="report-stats">
      <div><small>{t('总资产（虚拟）')}</small><strong>{formatMoney(account.total_assets)}</strong></div>
      <div><small>{t('可用资金（虚拟）')}</small><strong>{formatMoney(account.available_cash)}</strong></div>
      <div><small>{t('持仓市值（虚拟）')}</small><strong>{formatMoney(account.position_value)}</strong></div>
      <div><small>{t('已成交')}</small><strong>{account.orders.filter(o => o.status === 'filled').length}</strong></div>
    </div>
    <p className="tiny muted">{t('归档不代表已清仓，持仓市值按本轮最后教学日的收盘价计算。')}</p>
    <AccountRecords key={id} account={account} readOnly/>
    <details className="round-reflections"><summary>{t('本轮计划与复盘')} · {account.reflections.length}</summary>
      {account.reflections.length ? account.reflections.map(row => <article key={row.id}><small>{dateText(row.created_at)}</small><h4>{t('交易前计划')}</h4><p>{row.plan}</p><h4>{t('交易后复盘')}</h4><p>{row.review}</p></article>) : <p className="muted">{t('本轮没有保存复盘。')}</p>}
    </details>
    <p className="round-versions">{account.data_version} · {account.rule_version}</p>
  </div>
}
