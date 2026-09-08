import { useLayoutEffect, useState } from 'react'
import * as Primitive from '@radix-ui/react-dialog'
import { ArrowLeft, ArrowRight, Check, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAction } from '../../lib/api'
import { Button } from '../../components/ui/button'
import { ErrorNote } from '../../components/shared'

const steps = [
  { target: 'welcome', title: '欢迎来到你的学习空间', text: '用一分钟认识这里。课程、模拟订单和学习奖励，都只记录在你自己的账号下。' },
  { target: 'account', title: '先认识你的模拟账户', text: '从 100,000 元虚拟资金开始。总资产、可用资金和持仓分别记录；提交委托后，要推进教学日才会处理成交。' },
  { target: 'path', title: '按章节，一步步掌握', text: '每章都有讲解和两道独立练习。通过练习后，经验与徽章自动保存，再解锁下一章。' },
  { target: 'practice', title: '动手练习，也留下一次思考', text: '自由模拟使用独立账户。订单、持仓、资金流水和复盘可按需打开查看，遇到疑问可以请教教学教练。' },
]

export default function Onboarding({ initialStep, onClose }: { initialStep: number; onClose: () => void }) {
  const [step, setStep] = useState(initialStep)
  const [box, setBox] = useState({ top: 90, left: 260, width: 400, height: 190 })
  const action = useAction<unknown, { step: number; status: string }>('/onboarding')
  const navigate = useNavigate()
  useLayoutEffect(() => {
    const element = document.querySelector(`[data-tour="${steps[step].target}"]`)
    const measure = () => {
      const rect = element?.getBoundingClientRect()
      if (rect) setBox({ top: rect.top - 5, left: rect.left - 5, width: rect.width + 10, height: rect.height + 10 })
    }
    measure()
    const observer = new ResizeObserver(measure)
    if (element) observer.observe(element)
    window.addEventListener('resize', measure)
    return () => { observer.disconnect(); window.removeEventListener('resize', measure) }
  }, [step])
  const width = Math.min(360, window.innerWidth - 32)
  const left = Math.max(16, Math.min(window.innerWidth - width - 16, box.left + box.width + width + 32 < window.innerWidth ? box.left + box.width + 18 : box.left - width - 18 > 16 ? box.left - width - 18 : box.left))
  const top = Math.max(16, Math.min(window.innerHeight - 340, box.height > 230 ? box.top + 20 : box.top + box.height + 18))
  const save = (next: number, status: string, finish = false) => action.mutate({ step: next, status }, { onSuccess: () => { if (status === 'pending') setStep(next); else { onClose(); if (finish) navigate('/learn/account') } } })
  return <Primitive.Root open onOpenChange={open => { if (!open && !action.isPending) save(step, 'skipped') }}><Primitive.Portal>
    <Primitive.Overlay className="tour-overlay" />
    <div className="tour-spotlight" style={box} aria-hidden="true" />
    <Primitive.Content className="tour-tooltip" style={{ top, left, width }} onPointerDownOutside={e => e.preventDefault()}>
      <span className="eyebrow"><Sparkles size={15} />新手引导 · {step + 1} / {steps.length}</span>
      <Primitive.Title>{steps[step].title}</Primitive.Title><Primitive.Description>{steps[step].text}</Primitive.Description>
      <div className="tour-dots" aria-label={`第 ${step + 1} 步，共 ${steps.length} 步`}>{steps.map((_, i) => <i key={i} className={i === step ? 'active' : i < step ? 'done' : ''} />)}</div>
      <ErrorNote error={action.error} /><div className="tour-actions"><Button variant="ghost" size="sm" disabled={action.isPending} onClick={() => save(step, 'skipped')}>跳过引导</Button>{step > 0 && <Button variant="secondary" size="sm" disabled={action.isPending} aria-label="上一步" onClick={() => save(step - 1, 'pending')}><ArrowLeft size={16} /></Button>}<Button size="sm" disabled={action.isPending} onClick={() => step === steps.length - 1 ? save(step, 'completed', true) : save(step + 1, 'pending')}>{step === steps.length - 1 ? '开始第一课' : '下一步'}{step === steps.length - 1 ? <Check size={16} /> : <ArrowRight size={16} />}</Button></div>
      <p className="tiny muted">之后可从右上角账号菜单重新打开。</p>
    </Primitive.Content>
  </Primitive.Portal></Primitive.Root>
}
