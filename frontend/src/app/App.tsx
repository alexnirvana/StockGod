import { t, useLocale } from '../i18n'
import { useEffect, useRef, useState } from 'react';
import { Navigate, NavLink, Route, Routes, useNavigate, useLocation } from 'react-router-dom';
import { BarChart3, Bell, ChartNoAxesCombined, ChevronRight, FlaskConical, Gamepad2, House, Search, ShieldCheck, UserRound, X, BookOpen } from 'lucide-react';
import { MotionConfig } from 'motion/react';
import { useStateQuery, api } from '../lib/api';
import { Button } from '../components/ui/button';
import { Dialog } from '../components/ui/dialog';
import { ErrorNote, Loading } from '../components/shared';
import { useQueryClient } from '@tanstack/react-query';
import Onboarding from '../features/auth/Onboarding';
import { announceAuthChange } from '../features/auth/Auth';
import Home from '../features/learning/Home';
import Learning, { LearningMap } from '../features/learning/Learning';
import Trading from '../features/trading/Trading';
import Experiments from '../features/experiments/Experiments';
import Profile from '../features/learning/Profile';
import ReviewDialog from '../features/learning/ReviewDialog';
import DataStatus from './DataStatus';
import LanguageSwitcher from '../i18n/LanguageSwitcher';
export default function App() {
    useLocale();
    const links = [{ to: '/', label: t("学习主页"), icon: House }, { to: '/learn', label: t("交易训练"), icon: ChartNoAxesCombined }, { to: '/simulate', label: t("自由模拟"), icon: Gamepad2 }, { to: '/experiments', label: t("策略实验"), icon: FlaskConical }, { to: '/profile', label: t("学习档案"), icon: BarChart3 }, { to: '/status', label: t("数据状态"), icon: ShieldCheck }];
    const query = useStateQuery();
    const state = query.data;
    const navigate = useNavigate();
    const location = useLocation();
    const [search, setSearch] = useState('');
    const [guide, setGuide] = useState(false);
    const [guideStart, setGuideStart] = useState(0);
    const [userMenu, setUserMenu] = useState(false);
    const [logoutError, setLogoutError] = useState<Error | null>(null);
    const [loggingOut, setLoggingOut] = useState(false);
    const client = useQueryClient();
    const [notifications, setNotifications] = useState(false);
    const searchRef = useRef<HTMLInputElement>(null);
    useEffect(() => {
        if (state?.player.guide_status === 'pending' && !guide) {
            navigate('/', { replace: true });
            setGuideStart(state.player.guide_step);
            setGuide(true);
        }
    }, [state?.player.id, state?.player.guide_status]);
    const logout = async () => {
        setLoggingOut(true);
        setLogoutError(null);
        try {
            await api('/auth/logout', {});
            await client.cancelQueries();
            client.removeQueries({ predicate: q => q.queryKey[0] !== 'auth' });
            client.setQueryData(['auth'], null);
            announceAuthChange();
            navigate('/login', { replace: true });
        }
        catch (error) {
            setLogoutError(error as Error);
        }
        finally {
            setLoggingOut(false);
        }
    };
    const next = state?.courses.find(c => !c.completed) || state?.courses[0];
    useEffect(() => {
        const handler = (e: KeyboardEvent) => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            searchRef.current?.focus();
        } if (e.key === 'Escape')
            setSearch(''); };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, []);
    useEffect(() => { window.scrollTo(0, 0); }, [location.pathname]);
    const start = () => navigate('/learn/' + next?.id);
    const matches = state?.courses.filter(c => (c.title + c.goal).includes(search));
    return <MotionConfig reducedMotion={state?.player.reduced_motion ? 'always' : 'user'}><div className="app-shell" data-reduced-motion={state?.player.reduced_motion}>
    <a className="skip-link" href="#main">{t("跳到主要内容")}</a>
    <aside className="sidebar">
      <NavLink className="brand" to="/" aria-label={t("我是股神，回到学习主页")}><img src="/favicon.svg" alt=""/><span><strong>{t("我是股神")}</strong><small>Stock God</small></span></NavLink>
      <nav aria-label={t("主导航")}>{links.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}><Icon size={22}/><span>{label}</span><ChevronRight className="nav-arrow" size={15}/></NavLink>)}</nav>
      <div className="sidebar-art" aria-hidden="true"><div><p>{t("投资认知进化")}<br />{t("从这里开始")}</p><small>A BETTER INVESTOR</small></div></div>
      <div className="sidebar-footer"><span className="status-dot"/>{t("现在学习 · 更好的自己")}<small>{t("个人学习空间 · v0.5")}</small></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><LanguageSwitcher authenticated={!!state} />
        <div className="breadcrumb"><span>{t("我的学习空间")}</span><ChevronRight size={14}/><strong>{links.find(l => l.to === '/' ? location.pathname === '/' : location.pathname.startsWith(l.to))?.label || t("学习地图")}</strong></div>
        <div className="search-wrap"><Search size={17}/><input ref={searchRef} value={search} onChange={e => setSearch(e.target.value)} placeholder={t("搜索课程、知识点或问题…")} aria-label={t("搜索课程")}/><kbd>⌘ K</kbd>{search && <button aria-label={t("清除搜索")} onClick={() => setSearch('')}><X size={15}/></button>}
          {search && <div className="search-results">{matches?.length ? matches.map(c => <button key={c.id} onClick={() => { navigate(c.locked ? '/map' : '/learn/' + c.id); setSearch(''); }}><BookOpen size={16}/><span>{c.title}<small>{c.locked ? t("需先完成前置章节") : c.goal}</small></span></button>) : <p>{t("没有匹配的课程，试试“账户”或“订单”。")}</p>}</div>}
        </div>
        <button className="notification-button" aria-label={t("学习提醒")} onClick={() => setNotifications(true)}><Bell size={21}/>{state?.courses.some(c => c.review_due) && <i />}</button>
        <button className="user-menu" onClick={() => setUserMenu(true)} aria-label={t("账号菜单")}><span className="avatar"><UserRound size={23}/></span><span><strong>{t("你好，")}{state?.player.name || t("学员")}</strong><small>{t("持续学习，成为更好的自己")}</small></span></button>
      </header>
      <main id="main" className="main-content">
        {query.isPending ? <Loading /> : query.error ? <div className="connection-error"><ErrorNote error={query.error}/><p>{t("暂时无法读取你的学习记录，请稍后重试。")}</p><Button onClick={() => query.refetch()}>{t("重新连接")}</Button></div> : state && <Routes>
          <Route path="/" element={<Home state={state} onStart={start} onReview={() => setNotifications(true)}/>}/>
          <Route path="/map" element={<LearningMap state={state}/>}/>
          <Route path="/learn" element={<Navigate to={'/learn/' + next?.id} replace/>}/>
          <Route path="/learn/:lessonId" element={<Learning state={state}/>}/>
          <Route path="/simulate" element={<Trading state={state}/>}/>
          <Route path="/experiments" element={<Experiments />}/>
          <Route path="/profile" element={<Profile state={state} onReview={() => setNotifications(true)}/>}/>
          <Route path="/status" element={<DataStatus state={state}/>}/>
          <Route path="*" element={<div className="empty-state"><h1>{t("这个学习入口不存在")}</h1><Button onClick={() => navigate('/')}>{t("返回学习主页")}</Button></div>}/>
        </Routes>}
      </main>
      <footer className="workspace-footer"><ShieldCheck size={13}/>{t("教学示例 · 不进行真实交易")}<span>{t("学习优先 · 结果可解释")}</span></footer>
    </div>
    {guide && state && <Onboarding initialStep={guideStart} onClose={() => setGuide(false)}/>}
    <Dialog open={userMenu} onOpenChange={setUserMenu} title={t("我的账号")} description={t("当前登录：") + (state?.player.username || '')}>
      <div className="account-menu-actions"><Button variant="secondary" onClick={() => { setUserMenu(false); navigate('/profile'); }}>{t("查看学习档案")}</Button><Button variant="secondary" onClick={() => { setUserMenu(false); navigate('/status'); }}>{t("修改学习昵称与偏好")}</Button><Button variant="secondary" onClick={() => { setUserMenu(false); navigate('/'); setGuideStart(0); setGuide(true); }}>{t("重新查看新手引导")}</Button><ErrorNote error={logoutError}/><Button variant="danger" disabled={loggingOut} onClick={logout}>{loggingOut ? t("正在退出…") : t("退出登录")}</Button></div>
    </Dialog>
    <ReviewDialog open={notifications} onOpenChange={setNotifications}/>
  </div></MotionConfig>;
}
