import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { Job } from '../../lib/types'
import { api, dateText, formatMoney } from '../../lib/api'
import { t, useLocale } from '../../i18n'
import { Button } from '../../components/ui/button'
import { ErrorNote, Loading } from '../../components/shared'
import { ComparisonChart } from '../../components/Chart'

export type ComparisonReport = {
  start_day: number; end_day: number; data_version: string; notes: string[]
  rows: { id: string; params: Job['params']; curve: { day: number; value: string }[];
    common_return: string; common_drawdown: string; original_return: string;
    original_fees: string; original_trade_count: number }[]
}

export function Comparison({ jobs }: { jobs: Job[] }) {
  const locale = useLocale()
  const [selected, setSelected] = useState<string[]>([])
  const [submitted, setSubmitted] = useState<string[]>([])
  const report = useQuery({ queryKey: ['comparison', submitted, locale],
    queryFn: () => api<ComparisonReport>('/experiments/comparison?' + new URLSearchParams(submitted.map(id => ['ids', id]))),
    enabled: submitted.length >= 2, placeholderData: undefined })
  const completed = jobs.filter(job => job.status === 'completed' && job.result)
  return <div className="comparison">
    <p>{t('选择两到三个已完成实验。曲线会按共同区间的首日收盘净值归一为 100。')}</p>
    {completed.length < 2 && <p className="empty-note">{t('先运行至少两个实验，再比较参数带来的变化。')}</p>}
    <div className="comparison-picker">{completed.map(job => <label key={job.id}>
      <input type="checkbox" checked={selected.includes(job.id)} disabled={selected.length === 3 && !selected.includes(job.id)}
        onChange={e => { setSelected(ids => e.target.checked ? [...ids, job.id] : ids.filter(id => id !== job.id)); setSubmitted([]) }}/>
      <span><strong>MA {job.params.short_window}/{job.params.long_window} · {job.params.allocation}%</strong><small>{dateText(job.created_at)} · {job.id.slice(0, 6)}</small></span>
    </label>)}</div>
    <Button size="sm" disabled={selected.length < 2 || report.isFetching} onClick={() => setSubmitted([...selected])}>{t('比较所选实验')}</Button>
    {submitted.length >= 2 && <>{report.isPending ? <Loading/> : report.error ? <ErrorNote error={report.error}/> : report.data && <>
      <h3>{t('共同区间：第 {{start}} 至 {{end}} 教学日', { start: report.data.start_day + 1, end: report.data.end_day + 1 })}</h3>
      <ComparisonChart report={report.data}/>
      <div className="table-scroll"><table><thead><tr><th>{t('实验参数')}</th><th>{t('共同区间收益')}</th><th>{t('共同区间回撤')}</th><th>{t('原始区间收益')}</th><th>{t('原始总费用')}</th><th>{t('原始成交数')}</th></tr></thead>
        <tbody>{report.data.rows.map(row => <tr key={row.id}><td>MA {row.params.short_window}/{row.params.long_window} · {row.params.allocation}%<small className="muted"> · {row.id.slice(0, 6)}</small></td><td>{row.common_return}%</td><td>{row.common_drawdown}%</td><td>{row.original_return}%</td><td>{formatMoney(row.original_fees)}</td><td>{row.original_trade_count}</td></tr>)}</tbody></table></div>
      <div className="report-notes">{report.data.notes.map(note => <p key={note}>{note}</p>)}</div>
    </>}</>}
  </div>
}
