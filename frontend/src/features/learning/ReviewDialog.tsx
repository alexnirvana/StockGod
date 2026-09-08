import { t, useLocale, i18n } from '../../i18n'
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { BookOpen, Check, ChevronRight } from 'lucide-react';
import { api, dateText, useAction } from '../../lib/api';
import type { ReviewItem, ReviewQueue, ReviewResult } from '../../lib/types';
import { Dialog } from '../../components/ui/dialog';
import { Button } from '../../components/ui/button';
import { ErrorNote, Loading } from '../../components/shared';
export default function ReviewDialog({ open, onOpenChange }: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}) {
    useLocale();
    return <Dialog wide open={open} onOpenChange={onOpenChange} title={t("错题与知识复习")} description={t("换一个案例，检验理解。答对后依次间隔 1、3、7 天巩固；答错则重新开始，不影响已获奖励。")}>
    {open && <ReviewContent close={() => onOpenChange(false)}/>}
  </Dialog>;
}
function ReviewContent({ close }: {
    close: () => void;
}) {
    useLocale();
    const query = useQuery({ queryKey: ['reviews', i18n.language], queryFn: () => api<ReviewQueue>('/reviews'), refetchInterval: 60000 });
    // Keep the presented question stable while the queue refreshes after an answer.
    const [selected, setSelected] = useState<ReviewItem | null>(null);
    if (selected)
        return <ReviewQuestion key={selected.id + ':' + selected.revision} item={selected} back={() => setSelected(null)} close={close}/>;
    if (query.isPending)
        return <Loading />;
    if (query.error || !query.data)
        return <><ErrorNote error={query.error}/><Button onClick={() => query.refetch()}>{t("重新加载复习列表")}</Button></>;
    const { items, summary } = query.data;
    return <div className="review-content">
    <div className="review-summary"><span><strong>{summary.due}</strong>{t("现在可复习")}</span><span><strong>{summary.scheduled}</strong>{t("已安排巩固")}</span><span><strong>{summary.mastered}</strong>{t("已完成巩固")}</span></div>
    {!items.length ? <div className="empty-state"><Check className="teal-text" size={30}/><h3>{t("还没有需要复习的错题")}</h3><p>{t("独立练习中的错题会按知识点保存在这里。")}</p><Button asChild variant="secondary"><Link to="/map" onClick={close}>{t("前往学习地图")}</Link></Button></div> : <>
      {!summary.due && <p className="success-note" role="status">{t("当前复习已完成。")}{summary.next_due_at ? t("下次复习：") + dateText(summary.next_due_at) + t("（北京时间）") : t("继续学习，遇到的新问题会记录在这里。")}</p>}
      <div className="review-list">{items.map(item => <div className="review-row" key={item.id}><BookOpen className={item.due ? 'amber-text' : 'teal-text'} size={21}/><div><h3>{item.title}</h3><small>{item.stage === 4 ? t("已完成本轮巩固") : item.due ? t("待复习 · ") + item.review_count + t(" 次复习记录") : t("下次 ") + dateText(item.due_at!) + t(" · 北京时间")}<span>{t("连续答对")}{item.stage}{t("/ 4 次")}</span></small></div>{item.due ? <Button size="sm" variant="secondary" onClick={() => setSelected(item)}>{t("开始复习")}<ChevronRight size={15}/></Button> : <span className="muted tiny">{item.stage === 4 ? t("已巩固") : t("等待到期")}</span>}</div>)}</div>
    </>}
  </div>;
}
function ReviewQuestion({ item, back, close }: {
    item: ReviewItem;
    back: () => void;
    close: () => void;
}) {
    useLocale();
    const [answer, setAnswer] = useState(-1);
    const action = useAction<ReviewResult, {
        answer: number;
        revision: number;
        variant: number;
        content_version: number;
    }>('/reviews/' + item.id + '/answers');
    return <form className="quiz review-quiz" onSubmit={event => { event.preventDefault(); action.mutate({ answer, revision: item.revision, variant: item.variant, content_version: item.content_version }); }}>
    <span className="eyebrow">{t("KNOWLEDGE REVIEW · 独立判断")}</span><h2>{item.title}</h2>
    {!action.data ? <fieldset disabled={action.isPending}><legend>{item.question.prompt}</legend>{item.question.options.map((text, index) => <label key={index} className={'quiz-option ' + (answer === index ? 'selected' : '')}><input type="radio" name="review-answer" checked={answer === index} onChange={() => setAnswer(index)}/><span className="option-letter">{String.fromCharCode(65 + index)}</span>{text}</label>)}</fieldset> : <div className={'quiz-result ' + (action.data.passed ? 'passed' : '')} role="status"><h3>{action.data.message}</h3><p>{action.data.explanation}</p><p>{action.data.passed ? action.data.due_at ? t("下次复习：") + dateText(action.data.due_at) + t("（北京时间）") : t("四次间隔复习已完成。以后再次答错时，会重新安排。") : t("回到列表后会提供另一个案例。也可以先重看本课讲解。")}</p><small>{t("复习记录已保存 · 课程经验与徽章保持不变")}</small></div>}
    <ErrorNote error={action.error}/>
    <div className="quiz-navigation"><Button variant="secondary" type="button" disabled={action.isPending} onClick={back}>{t("返回复习列表")}</Button>{action.data ? <Button asChild variant="ghost"><Link to={'/learn/' + item.lesson_id} onClick={close}>{t("重看本课讲解")}</Link></Button> : <Button disabled={answer < 0 || action.isPending}>{action.isPending ? t("正在保存…") : t("提交复习答案")}<ChevronRight size={16}/></Button>}</div>
  </form>;
}
