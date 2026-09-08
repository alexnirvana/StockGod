import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Bot, Database, Download, Globe2, HardDrive, Settings2, ShieldCheck } from 'lucide-react'
import type { State, Status } from '../lib/types'
import { api, useAction } from '../lib/api'
import { Panel, PageHeader, Loading, ErrorNote } from '../components/shared'
import { Dialog } from '../components/ui/dialog'
import { Button } from '../components/ui/button'

export default function DataStatus({ state }: { state: State }) {
  const [rulesOpen, setRulesOpen] = useState(false)
  const query = useQuery({ queryKey: ['status'], queryFn: () => api<Status>('/status'), refetchInterval: 15000 })
  const [name, setName] = useState(state.player.name)
  const [reduced, setReduced] = useState(state.player.reduced_motion)
  const save = useAction<unknown, { name: string; reduced_motion: boolean }>('/profile')
  const status = query.data
  return <div><PageHeader eyebrow="DATA & SETTINGS / 数据状态" title="清楚知道，你正在使用什么" description="查看数据来源、服务状态和模拟规则，管理你的账号偏好。" />
    {query.isPending ? <Loading /> : query.error ? <ErrorNote error={query.error} /> : status && <><div className="data-status-grid">{[
      [Database, '教学场景', '已就绪', '60 日固定虚构数据，支持离线学习和模拟。', true],
      [Globe2, '真实历史行情', '尚未接入', '尚未配置或核验供应商，不展示伪造的历史行情。', false],
      [HardDrive, '实验 Worker', status.worker ? '运行中' : '未在线', status.worker ? '负责执行持久化队列中的教学回测任务。' : '实验可进入队列，启动 Worker 后才会执行。', status.worker],
      [Bot, '教学教练', '预设讲解可用', '无需外部模型或密钥，提供确定性的课程讲解。', true]
    ].map(([Icon, title, value, desc, ready]) => { const I = Icon as typeof Database; return <Panel key={String(title)} className="service-card"><I size={28} className="blue" /><span className={ready ? 'teal-text' : 'amber-text'}>{String(value)}</span><h2>{String(title)}</h2><p>{String(desc)}</p></Panel> })}</div>
      <div className="settings-grid"><Panel title="模拟规则与数据版本" icon={<ShieldCheck className="blue" size={20} />}><p className="muted">教学示例 · 非真实行情</p><div className="settings-summary"><Database className="blue" size={30} /><strong>{status.database === 'mysql' ? 'MySQL' : status.database}</strong><span>账号 @{state.player.username}</span><small>课程、订单、复盘与实验独立保存</small></div><Button variant="secondary" onClick={() => setRulesOpen(true)}>查看规则与版本详情</Button><Dialog wide open={rulesOpen} onOpenChange={setRulesOpen} title="模拟规则与数据版本" description="理解教学场景的假设与边界。"><dl className="settings-details"><dt>数据标识</dt><dd>教学示例 · 非真实行情</dd><dt>数据版本</dt><dd>{status.teaching.version}</dd><dt>规则版本</dt><dd>{status.rules.version}</dd><dt>业务数据库</dt><dd>{status.database === 'mysql' ? 'MySQL · 用户数据独立保存' : status.database === 'sqlite' ? 'SQLite · 开发模式' : status.database}</dd><dt>前向模拟</dt><dd>尚未接入后续真实行情</dd><dt>成交方式</dt><dd>下一教学日开盘估算；限价不满足则到期</dd><dt>模拟范围</dt><dd>虚构普通股票、只做多、100 股整手、次日可卖</dd><dt>暂不支持</dt><dd>企业行动、特殊板块、部分成交和真实行情规则包</dd></dl><p className="muted">{status.rules.commission_note}</p><details><summary>查看规则参考资料</summary><div className="source-links">{status.rules.sources.map(s => <a key={s.url} href={s.url} target="_blank" rel="noreferrer">{s.title} ↗</a>)}</div></details></Dialog></Panel>
      <div className="settings-stack"><Panel title="学习偏好" icon={<Settings2 className="blue" size={20} />}><form className="settings-form" onSubmit={e => { e.preventDefault(); save.mutate({ name, reduced_motion: reduced }) }}><label className="field">学习昵称<input value={name} onChange={e => setName(e.target.value)} maxLength={24} required /></label><label className="check-label"><input type="checkbox" checked={reduced} onChange={e => setReduced(e.target.checked)} />减少界面动画</label><ErrorNote error={save.error} />{save.isSuccess && <p className="success-note" role="status">偏好已保存。</p>}<Button disabled={save.isPending || !name.trim()}>保存偏好</Button></form></Panel><Panel title="我的数据导出" icon={<Download className="blue" size={20} />}><p className="muted">导出当前账号的学习、订单和账本记录，便于检查与留存。</p><Button asChild variant="secondary"><a href="/api/export" download>导出我的记录 <Download size={16} /></a></Button><p className="tiny muted">JSON 导出用于查阅；恢复账户请使用数据库备份。</p></Panel></div></div>
    </>}
  </div>
}

