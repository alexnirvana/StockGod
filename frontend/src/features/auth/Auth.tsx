import { t, useLocale, i18n, setLocale } from '../../i18n'
import LanguageSwitcher from '../../i18n/LanguageSwitcher'
import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, BookOpen, Eye, EyeOff, ShieldCheck, Target, TrendingUp } from 'lucide-react';
import { api, ApiError, setActiveUser } from '../../lib/api';
import type { AuthUser } from '../../lib/types';
import { Button } from '../../components/ui/button';
import { ErrorNote, Loading } from '../../components/shared';
import App from '../../app/App';
export const announceAuthChange = () => localStorage.setItem('stockgod.auth-change', crypto.randomUUID());
export default function AuthRoot() {
    useLocale();
    const client = useQueryClient();
    const location = useLocation();
    const query = useQuery({ queryKey: ['auth'], queryFn: async () => {
            try {
                return await api<{
                    user: AuthUser;
                }>('/auth/me');
            }
            catch (e) {
                if (e instanceof ApiError && e.status === 401)
                    return null;
                throw e;
            }
        }, retry: false, staleTime: 0 });
    useEffect(() => {
        if (query.data?.user.locale) void setLocale(query.data.user.locale);
    }, [query.data?.user.id, query.data?.user.locale]);
    useEffect(() => {
        const expired = () => { void client.cancelQueries(); client.removeQueries({ predicate: q => q.queryKey[0] !== 'auth' }); client.setQueryData(['auth'], null); };
        const changed = (e: StorageEvent) => { if (e.key === 'stockgod.auth-change') {
            void client.cancelQueries();
            client.removeQueries({ predicate: q => q.queryKey[0] !== 'auth' });
            client.setQueryData(['auth'], null);
            void client.invalidateQueries({ queryKey: ['auth'] });
        } };
        window.addEventListener('stockgod:unauthorized', expired);
        window.addEventListener('storage', changed);
        return () => { window.removeEventListener('stockgod:unauthorized', expired); window.removeEventListener('storage', changed); };
    }, [client]);
    if (query.isPending)
        return <Loading />;
    if (query.error)
        return <div className="auth-connection"><ErrorNote error={query.error}/><Button onClick={() => query.refetch()}>{t("重新连接")}</Button></div>;
    if (!query.data) {
        setActiveUser('anonymous');
        return location.pathname === '/login' ? <AuthPage /> : <Navigate to="/login" replace/>;
    }
    setActiveUser(query.data.user.id);
    return location.pathname === '/login' ? <Navigate to="/" replace/> : <App key={query.data.user.id}/>;
}
function AuthPage() {
    useLocale();
    const [register, setRegister] = useState(false);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [visible, setVisible] = useState(false);
    const client = useQueryClient();
    const navigate = useNavigate();
    const mutation = useMutation({ mutationFn: () => api<{
            user: AuthUser;
        }>(register ? '/auth/register' : '/auth/login', { username, password, ...(register ? { locale: i18n.language } : {}) }), onSuccess: async (data) => {
            await client.cancelQueries();
            client.removeQueries({ predicate: q => q.queryKey[0] !== 'auth' });
            client.setQueryData(['auth'], data);
            announceAuthChange();
            navigate('/', { replace: true });
        } });
    const mismatch = register && !!confirm && password !== confirm;
    return <main className="auth-page"><div className="auth-language"><LanguageSwitcher /></div>
    <section className="auth-story"><div className="auth-brand"><img src="/favicon.svg" alt=""/><div><strong>{t("我是股神")}</strong><span>STOCK GOD</span></div></div>
      <div className="auth-intro"><span className="eyebrow">LEARN. PRACTICE. GROW.</span><h1>{t("每一次理解，")}<br />{t("都是你的成长。")}</h1><p>{t("从第一课到第一次模拟交易，")}<br />{t("让知识与练习，成为属于你的记录。")}</p></div>
      <div className="auth-features"><span><BookOpen />{t("章节课程")}</span><span><TrendingUp />{t("模拟交易")}</span><span><Target />{t("独立练习")}</span></div>
      <p className="auth-safety"><ShieldCheck size={17}/>{t("仅使用虚拟资金 · 不进行真实交易")}</p>
    </section>
    <section className="auth-form-panel"><div className="auth-form-content"><span className="eyebrow">YOUR LEARNING SPACE</span><h2>{register ? t("建立你的学习账号") : t("欢迎回来")}</h2><p className="muted">{register ? t("学习进度、订单与复盘，都会保存在你的账号下。") : t("登录后，继续上一次的学习。")}</p>
      <div className="auth-tabs" role="tablist" aria-label={t("账号入口")}><button role="tab" aria-selected={!register} onClick={() => { setRegister(false); mutation.reset(); }}>{t("登录")}</button><button role="tab" aria-selected={register} onClick={() => { setRegister(true); mutation.reset(); }}>{t("注册")}</button></div>
      <form onSubmit={e => { e.preventDefault(); if (!mismatch)
        mutation.mutate(); }}>
        <label className="field">{t("用户名")}<input autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} pattern="[A-Za-z0-9_]{3,32}" minLength={3} maxLength={32} placeholder={t("3–32 位字母、数字或下划线")} required/></label>
        <label className="field">{t("密码")}<div className="password-field"><input type={visible ? 'text' : 'password'} autoComplete={register ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} minLength={10} maxLength={128} placeholder={t("至少 10 位，建议使用较长的密码")} required/><button type="button" aria-label={visible ? t("隐藏密码") : t("显示密码")} onClick={() => setVisible(!visible)}>{visible ? <EyeOff size={18}/> : <Eye size={18}/>}</button></div></label>
        {register && <label className="field">{t("确认密码")}<input type={visible ? 'text' : 'password'} autoComplete="new-password" value={confirm} onChange={e => setConfirm(e.target.value)} minLength={10} maxLength={128} placeholder={t("再次输入密码")} required/></label>}
        {mismatch && <p className="form-validation" role="alert">{t("两次输入的密码不一致。")}</p>}<ErrorNote error={mutation.error}/>
        <Button className="full" disabled={mutation.isPending || mismatch || register && !confirm}>{mutation.isPending ? t("请稍候…") : register ? t("注册并开始学习") : t("登录")}<ArrowRight size={18}/></Button>
      </form>
      <p className="auth-switch">{register ? t("已经有账号？") : t("还没有账号？")}<button className="text-link" onClick={() => { setRegister(!register); mutation.reset(); }}>{register ? t("去登录") : t("创建账号")}</button></p>
      <div className="auth-private"><ShieldCheck size={16}/><span>{t("个人进度独立保存 · 首次登录提供新手引导")}</span></div>
    </div></section>
  </main>;
}
