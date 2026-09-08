import ListeningHistory from '../audio/ListeningHistory'
import { t, useLocale } from '../../i18n'
import { useState } from 'react';
import { Dialog } from '../../components/ui/dialog';
import { Link } from 'react-router-dom';
import { Award, BookOpen, Check, FileText, Target, Trophy, UserRound } from 'lucide-react';
import type { State } from '../../lib/types';
import { dateText } from '../../lib/api';
import { Panel, PageHeader } from '../../components/shared';
import { Button } from '../../components/ui/button';
export default function Profile({ state, onReview }: {
    state: State;
    onReview: () => void;
}) {
    useLocale();
    const [reflectionsOpen, setReflectionsOpen] = useState(false);
    const [listeningOpen, setListeningOpen] = useState(false);
    const completed = state.courses.filter(c => c.completed).length;
    return <div><PageHeader eyebrow={t("LEARNING PROFILE / 学习档案")} title={t("你的每一步，都有迹可循")} description={t("回看已掌握的知识、需要巩固的概念，以及每一次认真思考。")}/><div className="profile-banner"><span className="profile-avatar"><UserRound size={42}/></span><div><span className="eyebrow">LEARNER LEVEL {state.player.level}</span><h2>{state.player.name}</h2><p>{t("理解市场，认识自己")}</p></div><div className="profile-level"><strong>{state.player.xp} <small>XP</small></strong><div className="xp-track"><i style={{ width: (state.player.xp % 50) * 2 + '%' }}/></div><small>{t("距下一等级还需")}{50 - state.player.xp % 50} XP</small></div><div className="profile-count"><strong>{completed} / 5</strong><small>{t("已完成章节")}</small></div></div>
    <div className="profile-grid"><Panel title={t("知识掌握情况")} icon={<Target className="blue" size={20}/>}>{state.courses.map(c => <div className="mastery-row" key={c.id}><span className={'mastery-icon ' + (c.completed ? 'teal-text' : '')}>{c.completed ? <Check size={20}/> : <BookOpen size={20}/>}</span><div><h3>{c.title}</h3><small>{c.attempts ? t("最近正确率 ") + c.last_score + t("% · 共练习 ") + c.attempts + t(" 次") : t("从例子到独立练习，逐步理解")}</small></div><span className={c.review_due ? 'amber-text' : c.completed ? 'teal-text' : 'muted'}>{c.review_due ? t("待复习") : c.completed ? t("可独立完成") : t("未接触")}</span>{!c.locked && <Button variant="ghost" size="sm" asChild><Link to={'/learn/' + c.id}>{c.review_due || c.completed ? t("复习") : t("学习")}</Link></Button>}</div>)}</Panel><Panel title={t("我的徽章")} icon={<Trophy className="amber-text" size={20}/>}><div className="badge-collection">{state.courses.map((c, i) => <div key={c.id} className={!state.rewards.some(r => r.lesson_id === c.id) ? 'unearned' : ''}><span className={'badge-medal ' + (i % 2 ? 'violet' : '')}><Award size={31}/></span><h3>{c.badge}</h3><small>{state.rewards.some(r => r.lesson_id === c.id) ? t("已解锁 · +") + c.xp + ' XP' : t("完成独立练习后解锁")}</small></div>)}</div></Panel></div>
    <div className="profile-record-actions"><Button variant="secondary" onClick={() => setListeningOpen(true)}>{t("我的听课记录")}</Button><Button className="reflection-open" variant="secondary" onClick={() => setReflectionsOpen(true)}>{t("我的计划与复盘 ·")}{state.reflections.length}{t("条记录")}</Button></div><Dialog wide open={listeningOpen} onOpenChange={setListeningOpen} title={t("我的听课记录")} description={t("回到上一次收听的位置，继续学习。")}><ListeningHistory/></Dialog><Dialog wide open={reflectionsOpen} onOpenChange={setReflectionsOpen} title={t("我的计划与复盘")} description={t("只显示当前账号保存的练习记录。")}><Panel title={t("练习记录")} icon={<FileText className="blue" size={20}/>} className="reflection-list">{state.reflections.length ? state.reflections.map(r => <article key={r.id}><header><h3>{r.account_mode === 'free' ? t("自由模拟 · 第 {{round}} 轮", { round: r.round_number }) : t("教学账户")}</h3><time>{dateText(r.created_at)}</time></header><h4>{t("交易前计划")}</h4><p>{r.plan}</p><h4>{t("交易后复盘")}</h4><p>{r.review}</p></article>) : <div className="empty-state"><FileText size={30}/><h3>{t("把想法写下来，成长会更清晰")}</h3><p>{t("在课程的“复盘回顾”中保存计划和复盘，它们会一直留在这里。")}</p><Button variant="secondary" asChild><Link to="/learn">{t("去完成一次练习")}</Link></Button></div>}</Panel></Dialog>
    <Button className="review-profile-open" variant="secondary" onClick={onReview}>{t("错题与知识复习 ·")}{state.reviews.due}{t("个待复习 ·")}{state.reviews.scheduled}{t("个待巩固")}</Button>
  </div>;
}
