import LessonAudio from '../audio/LessonAudio'
import { t, useLocale, i18n } from '../../i18n'
import { useState, useEffect } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Markdown from 'react-markdown';
import { BookOpen, Check, ChevronRight, Flag, Lightbulb, LockKeyhole, MessageSquareText, Target, Trophy } from 'lucide-react';
import type { AccountContext, AnswerResult, Course, State } from '../../lib/types';
import { api, useAction } from '../../lib/api';
import { Button } from '../../components/ui/button';
import { Panel, ErrorNote, Loading, PageHeader, Coach } from '../../components/shared';
import { Dialog } from '../../components/ui/dialog';
import { TradingSurface } from '../trading/Trading';
export function LearningMap({ state }: {
    state: State;
}) {
    useLocale();
    return <div><PageHeader eyebrow={t("LEARNING PATH / 学习地图")} title={t("从第一次认识，到独立思考")} description={t("五个章节，一步步建立你的账户、交易与实验意识。")}/><div className="full-learning-map">{state.courses.map((c, i) => <Panel key={c.id} className={'map-card ' + (c.locked ? 'locked' : c.completed ? 'completed' : 'current')}><span className="map-index">{String(i + 1).padStart(2, '0')}</span><div className="map-course"><span className="eyebrow">CHAPTER {String(i + 1).padStart(2, '0')} · {c.minutes}{t("分钟")}</span><h2>{c.title}</h2><p>{c.goal}</p><div className="map-metadata"><span><Trophy size={15}/>{c.xp} XP</span><span>{c.completed ? t("可独立完成") : c.locked ? t("完成前置章节后解锁") : t("等待探索")}</span></div></div>{c.locked ? <span className="locked-action"><LockKeyhole size={20}/>{t("未解锁")}</span> : <Button asChild variant={c.completed ? 'secondary' : 'default'}><Link to={'/learn/' + c.id}>{c.completed ? t("复习本章") : t("开始本章")}<ChevronRight size={16}/></Link></Button>}</Panel>)}</div></div>;
}
export default function Learning({ state }: {
    state: State;
}) {
    useLocale();
    const params = useParams();
    const [searchParams] = useSearchParams();
    const listen = searchParams.get("listen") === "1";
    const id = params.lessonId || state.courses.find(c => !c.completed)?.id || 'account';
    const query = useQuery({ queryKey: ['course', id, i18n.language], placeholderData: (old, previous) => previous?.queryKey[1] === id ? old : undefined, queryFn: () => api<Course>('/courses/' + id), retry: false });
    const [tab, setTab] = useState('lesson');
    const [contentOpen, setContentOpen] = useState(false);
    const [coachOpen, setCoachOpen] = useState(false);
    useEffect(() => { setTab('lesson'); setContentOpen(listen); }, [id, listen]);
    if (query.isPending)
        return <Loading />;
    if (query.error || !query.data)
        return <div><PageHeader eyebrow={t("LEARNING / 交易训练")} title={t("按自己的节奏，一步步来")} description={t("完成前置章节的独立练习后，新的关卡会自然解锁。")}/><ErrorNote error={query.error}/><Button asChild variant="secondary"><Link to="/map">{t("查看学习地图")}</Link></Button></div>;
    const c = query.data;
    const current = state.courses.find(x => x.id === c.id)!;
    return <div className="lesson-page"><PageHeader eyebrow={'CHAPTER ' + String(state.courses.indexOf(current) + 1).padStart(2, '0') + t(" / 交易训练")} title={c.title} description={c.goal}/>
    <div className="mission-path">{state.courses.map((course, i) => <Link key={course.id} className={(course.id === id ? 'active' : '') + (course.completed ? ' complete' : '')} to={course.locked ? '/map' : '/learn/' + course.id}><span>{course.completed ? <Check size={18}/> : i + 1}</span><div>{course.short_title}<small>{course.completed ? t("已掌握") : course.locked ? t("待解锁") : t("当前可学习")}</small></div>{course.locked && <LockKeyhole size={13}/>}</Link>)}</div>
    <div className="mission-layout"><div className="mission-main"><TradingSurface mode="tutorial" compact/>
      <Panel className="lesson-dock"><div className="dock-tabs" role="tablist" aria-label={t("课程内容")}>{[['lesson', t("学习讲解"), BookOpen], ['example', t("练习引导"), Lightbulb], ['quiz', t("独立练习"), Target], ['reflection', t("复盘回顾"), MessageSquareText]].map(([key, text, Icon]) => { const I = Icon as typeof BookOpen; return <button key={String(key)} role="tab" aria-selected={tab === key} className={tab === key ? 'active' : ''} onClick={() => { setTab(String(key)); setContentOpen(true); }}><I size={22}/><span>{String(text)}</span></button>; })}</div>
        <Dialog wide open={contentOpen} onOpenChange={setContentOpen} title={({ lesson: t("学习讲解"), example: t("练习引导"), quiz: t("独立练习"), reflection: t("复盘回顾") })[tab] || t("课程")} description={c.title}><div className="lesson-content">{tab === 'lesson' ? <><LessonAudio key={c.id + i18n.language} lessonId={c.id} initial={c.narration} requestedLocale={searchParams.get('audioLocale')}/><div className="markdown"><Markdown components={{ h1: ({ children }) => <h2 className="lesson-title">{children}</h2> }}>{c.body}</Markdown></div><Button onClick={() => setTab('example')}>{t("看一个练习")}<ChevronRight size={16}/></Button></> : tab === 'example' ? <div className="practice-guide"><span className="eyebrow">GUIDED PRACTICE</span><h2>{t("先动手，再独立判断")}</h2><p>{c.practice}</p><ol><li>{t("阅读本课讲解，理解练习要验证的概念。")}</li><li>{t("在上方的教学场景操作，查看订单或账户结果。")}</li><li>{t("收起讲解，在不同案例中完成独立练习。")}</li></ol>{c.id === 'strategy' && <Button asChild variant="secondary"><Link to="/experiments">{t("前往策略实验")}</Link></Button>}<Button onClick={() => setTab('quiz')}>{t("开始独立练习")}<Target size={17}/></Button></div> : tab === 'quiz' ? <Quiz key={id} course={c}/> : <ReflectionForm />}
        </div></Dialog>
      </Panel>
    </div><aside className="mission-aside"><Panel title={t("本次任务目标")} icon={<Flag className="amber-text" size={22}/>} className="objective-panel"><div className="objective-copy"><span className="eyebrow">YOUR NEXT STEP</span><h3>{c.title}</h3><p>{c.goal}</p><h4>{t("任务要求")}</h4><div className="objective-line"><BookOpen size={17}/><span>{t("理解课程中的例子与概念")}</span></div><div className="objective-line"><Target size={17}/><span>{c.practice}</span></div><div className={'objective-line ' + (current.completed ? 'teal-text' : '')}>{current.completed ? <Check size={17}/> : <span className="empty-check"/>}<span>{t("独立完成本课的两道练习")}</span></div><div className="reward-preview"><Trophy size={26}/><div><small>{t("首次完成奖励")}</small><strong>+{c.xp} XP <span>· {c.badge}</span></strong></div></div><Button className="full" variant="secondary" onClick={() => { setTab('quiz'); setContentOpen(true); }}>{t("完成独立练习")}<ChevronRight size={16}/></Button></div></Panel><Button variant="secondary" onClick={() => setCoachOpen(true)}>{t("请教教学教练")}</Button><Dialog open={coachOpen} onOpenChange={setCoachOpen} title={t("教学教练")} description={c.title}><Coach lessonId={id}/></Dialog><div className="mission-tip"><Lightbulb size={20}/><p>{t("遇到没理解的地方，可以重看讲解。通关看理解，不看盈亏。")}</p></div></aside></div>
  </div>;
}
function Quiz({ course }: {
    course: Course;
}) {
    useLocale();
    const [questionIndex, setQuestionIndex] = useState(0);
    const [answers, setAnswers] = useState<number[]>(course.questions!.map(() => -1));
    const action = useAction<AnswerResult, {
        answers: number[];
    }>('/courses/' + course.id + '/answers');
    return <form className="quiz" onSubmit={e => { e.preventDefault(); if (questionIndex < course.questions!.length - 1)
        setQuestionIndex(i => i + 1);
    else
        action.mutate({ answers }); }}><span className="eyebrow">INDEPENDENT PRACTICE</span><h2>{t("换个案例，检验你的理解")}</h2><p className="muted">{t("独立作答后，系统会解释原因。你可以重试，首次完成奖励只发放一次。")}</p>
    {!action.data && course.questions!.map((q, i) => i === questionIndex && <fieldset key={i}><legend><span>{String(i + 1).padStart(2, '0')}</span>{q.prompt}</legend>{q.options.map((text, option) => <label key={option} className={'quiz-option ' + (answers[i] === option ? 'selected' : '')}><input type="radio" name={'question-' + i} checked={answers[i] === option} onChange={() => { setAnswers(old => old.map((a, j) => j === i ? option : a)); action.reset(); }}/><span className="option-letter">{String.fromCharCode(65 + option)}</span>{text}</label>)}</fieldset>)}
    <ErrorNote error={action.error}/>
    {action.data && <div className={'quiz-result ' + (action.data.passed ? 'passed' : '')} role="status"><h3>{action.data.passed ? t("独立练习已完成") : t("还有一些地方值得再想想")} · {action.data.score}%</h3>{action.data.feedback.map((f, i) => <p key={i}><strong>{t("第 {{number}} 题", { number: i + 1 })} · {f.passed ? t("回答正确") : t("再想一想")}：</strong>{f.explanation}</p>)}{action.data.requirements.map(r => <p key={r} className="amber-text">{r}</p>)}{action.data.passed && <div className="completion-row"><Trophy className="amber-text"/><strong>{action.data.xp_awarded ? '+' + action.data.xp_awarded + ' XP · ' + course.badge : t("本课奖励已领取，复习进度已保存")}</strong><Link className="text-link" to="/map">{t("查看下一章节")}<ChevronRight size={16}/></Link></div>}</div>}
    <div className="quiz-navigation">{!action.data ? <><span className="muted tiny">{t("第 {{current}} / {{total}} 题", { current: questionIndex + 1, total: course.questions!.length })}</span>{questionIndex > 0 && <Button type="button" variant="secondary" disabled={action.isPending} onClick={() => setQuestionIndex(i => i - 1)}>{t("上一题")}</Button>}<Button disabled={action.isPending || answers[questionIndex] < 0}>{action.isPending ? t("正在检查…") : questionIndex === course.questions!.length - 1 ? t("提交答案") : t("下一题")}<ChevronRight size={16}/></Button></> : <Button type="button" variant="secondary" onClick={() => { action.reset(); setQuestionIndex(0); }}>{t("重新练习")}</Button>}</div>
  </form>;
}
export function ReflectionForm({ mode = 'tutorial', context }: { mode?: 'tutorial' | 'free'; context?: AccountContext }) {
    useLocale();
    const [plan, setPlan] = useState('');
    const [review, setReview] = useState('');
    const action = useAction<{
        message: string;
    }, {
        expected_account_id?: string;
        expected_day?: number;
        account_id: string;
        plan: string;
        review: string;
    }>('/reflections');
    return <form className="reflection-form" onSubmit={e => { e.preventDefault(); action.mutate({ account_id: mode, ...context, plan, review }); }}><span className="eyebrow">REFLECT & GROW</span><h2>{t("把一次练习，变成自己的经验")}</h2><label className="field">{t("交易前计划")}<textarea minLength={10} maxLength={2000} value={plan} onChange={e => setPlan(e.target.value)} placeholder={t("这次练习想验证什么？打算使用多少仓位？（至少 10 个字）")} required/></label><label className="field">{t("交易后复盘")}<textarea minLength={10} maxLength={2000} value={review} onChange={e => setReview(e.target.value)} placeholder={t("订单发生了什么？费用是否符合预期？下次会怎样改进？")} required/></label><ErrorNote error={action.error}/>{action.data && <p className="success-note" role="status">{action.data.message}</p>}<Button disabled={action.isPending || plan.trim().length < 10 || review.trim().length < 10}>{t("保存计划与复盘")}<Check size={17}/></Button></form>;
}
