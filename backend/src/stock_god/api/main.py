import hashlib
import json
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request, Query
from stock_god.i18n import LocalizedJSONResponse as JSONResponse, LOCALE, PATH, negotiate, translate
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select

from stock_god.db.models import Base, Player, Account, Order, Ledger, Position, Progress, RequestRecord, Reward, Attempt, Reflection, Job, iso_time
from stock_god.db.session import database, transaction, heartbeat_path, owned_session
from stock_god.learning.service import LESSONS, course, course_detail, evaluate
from stock_god.trading.engine import account_view, create_order, advance, cancel
from stock_god.trading import practice
from stock_god.adapters.data import PROVIDER, RULES
from stock_god.api.auth import auth_router, resolve_session, digest, public_player
from stock_god.db.models import ReviewItem, ReviewAttempt
from stock_god.learning import reviews
from stock_god.research.comparison import compare
from stock_god.learning import narration
from stock_god.learning.coach import ANSWERS as COACH_ANSWERS, topic as coach_topic
from stock_god.db.models import ListeningProgress
from fastapi.responses import FileResponse


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProfileBody(StrictBody):
    name: str = Field(min_length=1, max_length=24)
    reduced_motion: bool = False

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("请填写玩家昵称。")
        return value


class GuideBody(StrictBody):
    step: int = Field(ge=0, le=3)
    status: Literal['pending', 'completed', 'skipped'] = 'pending'


class LanguageBody(StrictBody):
    locale: Literal['zh-CN', 'en']


class AccountIntent(StrictBody):
    expected_account_id: str | None = Field(default=None, min_length=1, max_length=191)
    expected_day: int | None = Field(default=None, ge=0, le=59, strict=True)


class NewRoundBody(StrictBody):
    expected_account_id: str = Field(min_length=1, max_length=191)
    expected_day: int = Field(ge=0, le=59, strict=True)


class OrderBody(AccountIntent):
    symbol: Literal["SG001", "SG002"]
    side: Literal["buy", "sell"]
    quantity: int = Field(gt=0, le=1000000, strict=True)
    limit_price: Decimal = Field(gt=0, max_digits=8, decimal_places=2)

    @field_validator("quantity")
    @classmethod
    def lot(cls, value):
        if value % 100:
            raise ValueError("本教学场景使用整手数量，请输入 100 股的整数倍。")
        return value


class AnswersBody(StrictBody):
    answers: list[int] = Field(min_length=1, max_length=10)


class ReviewBody(StrictBody):
    answer: int = Field(ge=0, strict=True)
    revision: int = Field(ge=0, strict=True)
    variant: int = Field(ge=0, strict=True)
    content_version: int = Field(ge=1, strict=True)


class ReflectionBody(AccountIntent):
    account_id: Literal["tutorial", "free"] = "tutorial"
    plan: str = Field(min_length=10, max_length=2000)
    review: str = Field(min_length=10, max_length=2000)

    @field_validator("plan", "review")
    @classmethod
    def meaningful(cls, value):
        if len(value.strip()) < 10:
            raise ValueError("请至少写 10 个字，说明你的想法。")
        return value.strip()


class ExperimentBody(StrictBody):
    short_window: int = Field(default=5, ge=2, le=15)
    long_window: int = Field(default=15, ge=5, le=30)
    allocation: int = Field(default=30, ge=10, le=80)


class CoachBody(StrictBody):
    question: str = Field(min_length=1, max_length=500)
    lesson_id: str = "account"


def create_app(url=None):
    engine, factory = database(url)

    @asynccontextmanager
    async def lifespan(app):
        if url is not None:
            Base.metadata.create_all(engine)  # isolated test databases only
        yield
        engine.dispose()

    app = FastAPI(title="Stock God · Teaching Simulation API", version="0.6.0", lifespan=lifespan, default_response_class=JSONResponse)
    app.state.factory = factory
    origins = {x.strip().rstrip('/') for x in os.getenv('APP_ORIGINS', 'http://127.0.0.1:8080,http://localhost:8080,http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174,http://testserver').split(',')}
    hosts = {'api', 'testserver', '127.0.0.1', 'localhost'} | {urlparse(x).hostname for x in origins}
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(hosts))
    app.include_router(auth_router(factory))

    @app.middleware("http")
    async def authenticated_api(request: Request, call_next):
        if not request.url.path.startswith('/api/'):
            return await call_next(request)
        writing = request.method not in ('GET', 'HEAD', 'OPTIONS')
        origin = request.headers.get('origin')
        if writing and (origin and origin.rstrip('/') not in origins):
            return JSONResponse(status_code=403, content={'detail': '请求来源不受信任。'})
        if writing and request.headers.get('x-stockgod-client') != 'web':
            return JSONResponse(status_code=403, content={'detail': '请从应用页面提交请求。'})
        if request.url.path not in ('/api/health', '/api/auth/login', '/api/auth/register'):
            auth = resolve_session(factory, request)
            if not auth:
                return JSONResponse(status_code=401, content={'detail': '请先登录，继续你的学习。'})
            request.state.player_id = auth[0]
            if writing and not secrets.compare_digest(digest(request.headers.get('x-csrf-token', '')), auth[1]):
                return JSONResponse(status_code=403, content={'detail': '登录验证已失效，请刷新页面重试。'})
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.middleware('http')
    async def language_context(request: Request, call_next):
        locale_token = LOCALE.set(negotiate(request.headers.get('accept-language')))
        path_token = PATH.set(request.url.path)
        try:
            response = await call_next(request)
            response.headers.setdefault('Content-Language', LOCALE.get())
            response.headers['Vary'] = 'Accept-Language'
            return response
        finally:
            LOCALE.reset(locale_token)
            PATH.reset(path_token)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail}, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Do not echo submitted passwords or other input back in errors.
        errors = []
        for error in exc.errors():
            message = error['msg']
            if LOCALE.get() == 'zh-CN' and not any('\u4e00' <= c <= '\u9fff' for c in message):
                message = '输入格式不符合要求，请检查填写内容。'
            errors.append({'loc': error['loc'], 'type': error['type'], 'msg': message})
        return JSONResponse(status_code=422, content={'detail': errors})

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        import logging
        logging.getLogger("stock_god").exception("Unhandled API error: %s", request.url.path, exc_info=exc)
        # ServerErrorMiddleware renders after request contexts have unwound.
        token = LOCALE.set(negotiate(request.headers.get('accept-language')))
        try:
            return JSONResponse(status_code=500, content={"detail": "服务暂时无法完成请求，变更已回滚。请稍后重试并查看服务日志。"},
                                headers={'Content-Language': LOCALE.get(), 'Vary': 'Accept-Language', 'Cache-Control': 'no-store'})
        finally:
            LOCALE.reset(token)

    def mutate(player_id, path, key, body, operation):
        digest = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
        request_id = hashlib.sha256((player_id + ":" + path + ":" + key).encode()).hexdigest()
        with transaction(factory, player_id) as session:
            old = session.get(RequestRecord, request_id)
            if old:
                if old.fingerprint != digest:
                    raise HTTPException(409, "这个请求编号已经用于不同的操作内容。请刷新后重试。")
                return old.result
            result = operation(session)
            session.add(RequestRecord(id=request_id, player_id=player_id, fingerprint=digest, result=result))
            return result

    @app.get("/api/health")
    def health():
        with factory() as s:
            s.execute(select(Player.id).limit(1))
        return {"status": "ok", "data": "teaching"}

    @app.get("/api/state")
    def state(request: Request):
        with owned_session(factory, request.state.player_id) as s:
            p = s.get(Player, request.state.player_id)
            courses = [course(s, l["id"]) for l in LESSONS]
            last = s.scalar(select(Attempt).where(Attempt.player_id == request.state.player_id).order_by(Attempt.created_at.desc()).limit(1))
            rewards = s.scalars(select(Reward).where(Reward.player_id == request.state.player_id).order_by(Reward.created_at.desc())).all()
            return {"player": {**public_player(p), "name": p.name, "onboarded": p.onboarded, "xp": p.xp, "level": 1 + p.xp // 50, "reduced_motion": p.reduced_motion},
                    "courses": courses, "account": account_view(s, "tutorial"), "reviews": reviews.summary(s),
                    "rewards": [{"badge": r.badge, "xp": r.xp, "lesson_id": r.lesson_id, "created_at": iso_time(r.created_at)} for r in rewards],
                    "last_attempt": {"score": last.score, "lesson_id": last.lesson_id, "feedback": last.feedback, "created_at": iso_time(last.created_at)} if last else None,
                    "reflections": [{"id": r.id, "plan": r.plan, "review": r.review, "account_id": r.account_id, "account_mode": account_mode, "round_number": round_number, "created_at": iso_time(r.created_at)} for r, account_mode, round_number in s.execute(select(Reflection, Account.mode, Account.round_number).join(Account, Account.id == Reflection.account_id).where(Reflection.player_id == request.state.player_id, Account.player_id == request.state.player_id).order_by(Reflection.created_at.desc(), Reflection.id))]}

    @app.post("/api/profile")
    def profile(request: Request, body: ProfileBody, idempotency_key: str = Header(min_length=8, max_length=128)):
        def update(s):
            p = s.get(Player, request.state.player_id)
            p.name, p.reduced_motion, p.onboarded = body.name, body.reduced_motion, True
            return {"name": p.name, "reduced_motion": p.reduced_motion}
        return mutate(request.state.player_id, "profile", idempotency_key, body.model_dump(), update)

    @app.post('/api/onboarding')
    def onboarding(request: Request, body: GuideBody, idempotency_key: str = Header(min_length=8, max_length=128)):
        def update(s):
            player = s.get(Player, request.state.player_id)
            player.guide_step, player.guide_status = body.step, body.status
            return public_player(player)
        return mutate(request.state.player_id, 'onboarding', idempotency_key, body.model_dump(), update)

    @app.post('/api/preferences/language')
    def language_preference(request: Request, body: LanguageBody, idempotency_key: str = Header(min_length=8, max_length=128)):
        def update(s):
            player = s.get(Player, request.state.player_id)
            player.locale = body.locale
            return {'locale': player.locale}
        return mutate(request.state.player_id, 'language', idempotency_key, body.model_dump(), update)

    @app.get("/api/courses/{lesson_id}")
    def get_course(request: Request, lesson_id: str):
        with owned_session(factory, request.state.player_id) as s:
            result = course_detail(s, lesson_id)
            try:
                result["narration"] = narration.detail(s, "lesson-" + lesson_id, saved=True)
            except HTTPException as error:
                if error.status_code not in (404, 503):
                    raise
                result["narration"] = None
            return result

    @app.post("/api/courses/{lesson_id}/answers")
    def answers(request: Request, lesson_id: str, body: AnswersBody, idempotency_key: str = Header(min_length=8, max_length=128)):
        return mutate(request.state.player_id, "answers:" + lesson_id, idempotency_key, body.model_dump(), lambda s: evaluate(s, lesson_id, body.answers))

    @app.get('/api/reviews')
    def review_queue(request: Request):
        with owned_session(factory, request.state.player_id) as s:
            return reviews.queue(s)

    @app.post('/api/reviews/{review_id}/answers')
    def review_answer(request: Request, review_id: str, body: ReviewBody, idempotency_key: str = Header(min_length=8, max_length=128)):
        return mutate(request.state.player_id, 'review:' + review_id, idempotency_key, body.model_dump(), lambda s: reviews.answer(s, review_id, body))

    @app.get("/api/accounts/{mode}")
    def account(request: Request, mode: str):
        with owned_session(factory, request.state.player_id) as s:
            return account_view(s, mode)

    @app.get('/api/practice/rounds')
    def practice_history(request: Request, before: int | None = Query(default=None, ge=1), limit: int = Query(default=20, ge=1, le=50)):
        with owned_session(factory, request.state.player_id) as s:
            return practice.history(s, before, limit)

    @app.get('/api/practice/rounds/{account_id}')
    def practice_detail(request: Request, account_id: str):
        with owned_session(factory, request.state.player_id) as s:
            return practice.detail(s, account_id)

    @app.post('/api/practice/rounds')
    def new_practice(request: Request, body: NewRoundBody, idempotency_key: str = Header(min_length=8, max_length=128)):
        return mutate(request.state.player_id, 'practice:round', idempotency_key, body.model_dump(), lambda s: practice.start_round(s, body))

    @app.get("/api/accounts/{mode}/bars/{symbol}")
    def bars(request: Request, mode: str, symbol: str):
        from stock_god.trading.engine import get_account, require_versions
        if symbol not in PROVIDER.names:
            raise HTTPException(404, "没有这只教学股票。")
        with owned_session(factory, request.state.player_id) as s:
            a = get_account(s, mode)
            require_versions(a)
            return PROVIDER.visible(symbol, a.day)

    @app.post("/api/accounts/{mode}/orders")
    def submit_order(request: Request, mode: str, body: OrderBody, idempotency_key: str = Header(min_length=8, max_length=128)):
        return mutate(request.state.player_id, "order:" + mode, idempotency_key, body.model_dump(mode="json"), lambda s: create_order(s, mode, body))

    @app.post("/api/accounts/{mode}/orders/{order_id}/cancel")
    def cancel_order(request: Request, mode: str, order_id: str, idempotency_key: str = Header(min_length=8, max_length=128)):
        return mutate(request.state.player_id, "cancel:" + mode + ":" + order_id, idempotency_key, {}, lambda s: cancel(s, mode, order_id))

    @app.post("/api/accounts/{mode}/advance")
    def advance_day(request: Request, mode: str, body: AccountIntent, idempotency_key: str = Header(min_length=8, max_length=128)):
        return mutate(request.state.player_id, "advance:" + mode, idempotency_key, body.model_dump(), lambda s: advance(s, mode, body.expected_account_id, body.expected_day))

    @app.post("/api/reflections")
    def reflect(request: Request, body: ReflectionBody, idempotency_key: str = Header(min_length=8, max_length=128)):
        def save(s):
            from stock_god.trading.engine import get_account, require_context
            account = get_account(s, body.account_id)
            require_context(account, body.expected_account_id, body.expected_day)
            r = Reflection(id=str(uuid4()), player_id=request.state.player_id, plan=body.plan, review=body.review, account_id=account.id)
            s.add(r)
            return {"id": r.id, "message": "计划和复盘已保存到学习档案。"}
        return mutate(request.state.player_id, "reflection", idempotency_key, body.model_dump(), save)

    @app.get("/api/experiments")
    def experiments(request: Request):
        with owned_session(factory, request.state.player_id) as s:
            return [job_view(j) for j in s.scalars(select(Job).where(Job.player_id == request.state.player_id).order_by(Job.created_at.desc()).limit(30))]

    @app.get('/api/experiments/comparison')
    def experiment_comparison(request: Request, ids: list[str] = Query(min_length=2, max_length=3)):
        with owned_session(factory, request.state.player_id) as s:
            return compare(s, ids)

    @app.post("/api/experiments")
    def experiment(request: Request, body: ExperimentBody, idempotency_key: str = Header(min_length=8, max_length=128)):
        if body.short_window >= body.long_window:
            raise HTTPException(422, "短期窗口必须小于长期窗口，请调整参数。")
        def create(s):
            j = Job(id=str(uuid4()), player_id=request.state.player_id, params={**body.model_dump(), "data_version": PROVIDER.version, "strategy_version": "sma-v1", "rule_version": RULES["version"]})
            s.add(j)
            s.flush()
            return job_view(j)
        return mutate(request.state.player_id, "experiment", idempotency_key, body.model_dump(), create)

    @app.get("/api/status")
    def status(request: Request):
        heartbeat = heartbeat_path(engine)
        worker = False
        if heartbeat.exists():
            try:
                timestamp = json.loads(heartbeat.read_text())["timestamp"]
                worker = datetime.now(timezone.utc).timestamp() - timestamp < 45
            except (ValueError, KeyError, OSError):
                pass
        return {"database": engine.dialect.name, "teaching": {"status": "ready", "version": PROVIDER.version, "days": PROVIDER.last_day + 1},
                "worker": worker, "historical": "not_connected", "forward": "not_connected", "ai": "deterministic",
                "rules": RULES, "vnpy": "vendored_event_core_4.2.0"}

    @app.post("/api/coach")
    def coach(request: Request, body: CoachBody):
        with owned_session(factory, request.state.player_id) as s:
            detail = course_detail(s, body.lesson_id)
        selected = coach_topic(body.question)
        answer = COACH_ANSWERS[selected] if selected else translate(detail["goal"]) + " " + translate(detail["practice"])
        with owned_session(factory, request.state.player_id) as s:
            try:
                audio = narration.detail(s, 'coach-' + selected if selected else 'coach-lesson-' + body.lesson_id)
            except HTTPException as error:
                if error.status_code not in (404, 503):
                    raise
                audio = None
        return {"answer": answer, "source": detail["title"], "kind": "预设教学讲解", "narration": audio}

    @app.get('/api/narration/{track_id}/{locale}/{version}.mp3')
    def narration_audio(request: Request, track_id: str, locale: str, version: str):
        track = narration.track_for(track_id, locale, version)
        if track['course_id']:
            with owned_session(factory, request.state.player_id) as s:
                course_detail(s, track['course_id'])
        path = narration.ROOT / track['file']
        if not path.is_file():
            raise HTTPException(503, '课程音频尚未准备好，文字讲解仍可使用。')
        return FileResponse(path, media_type='audio/mpeg', headers={'Content-Language': track['locale']})

    @app.post('/api/courses/{lesson_id}/listening')
    def save_listening(request: Request, lesson_id: str, body: narration.BookmarkBody, idempotency_key: str = Header(min_length=8, max_length=128)):
        return mutate(request.state.player_id, 'listening:' + lesson_id, idempotency_key, body.model_dump(), lambda s: narration.save(s, lesson_id, body))

    @app.get('/api/courses/{lesson_id}/narration')
    def course_narration(request: Request, lesson_id: str, locale: Literal['zh-CN', 'en']):
        with owned_session(factory, request.state.player_id) as s:
            course_detail(s, lesson_id)
            return narration.detail(s, 'lesson-' + lesson_id, locale, saved=True)

    @app.get('/api/listening')
    def listening_history(request: Request):
        with owned_session(factory, request.state.player_id) as s:
            return narration.history(s)

    @app.get("/api/export")
    def export(request: Request):
        # Human-readable portable audit export. Full restoration uses DB backup.
        with owned_session(factory, request.state.player_id) as s:
            rows = {}
            account_ids = select(Account.id).where(Account.player_id == request.state.player_id)
            for model in (Player, Account, Progress, Reward, Attempt, Reflection, ReviewItem, ReviewAttempt, ListeningProgress, Job, Order, Position, Ledger):
                table = model.__table__
                if model is Player:
                    statement = select(table.c.id, table.c.username, table.c.name, table.c.xp, table.c.onboarded, table.c.reduced_motion, table.c.guide_step, table.c.guide_status, table.c.locale).where(table.c.id == request.state.player_id)
                elif model in (Order, Position, Ledger):
                    statement = select(table).where(table.c.account_id.in_(account_ids))
                else:
                    statement = select(table).where(table.c.player_id == request.state.player_id)
                rows[table.name] = [dict(row) for row in s.execute(statement).mappings()]
            return JSONResponse(content=json.loads(json.dumps({"format": "stockgod-audit-v3", "tables": rows}, default=str)),
                                headers={"Content-Disposition": 'attachment; filename="stockgod-audit.json"'})

    return app


def job_view(j):
    return {"id": j.id, "status": j.status, "params": j.params, "result": j.result, "error": j.error, "created_at": iso_time(j.created_at)}


app = create_app()
