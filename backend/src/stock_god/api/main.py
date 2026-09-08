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

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select

from stock_god.db.models import Base, Player, Account, Order, Ledger, Position, Progress, RequestRecord, Reward, Attempt, Reflection, Job, iso_time
from stock_god.db.session import database, transaction, heartbeat_path, owned_session
from stock_god.learning.service import LESSONS, course, course_detail, evaluate
from stock_god.trading.engine import account_view, create_order, advance, cancel
from stock_god.adapters.data import PROVIDER, RULES
from stock_god.api.auth import auth_router, resolve_session, digest, public_player
from stock_god.db.models import ReviewItem, ReviewAttempt
from stock_god.learning import reviews


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


class OrderBody(StrictBody):
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


class ReflectionBody(StrictBody):
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

    app = FastAPI(title="我是股神 · 教学模拟 API", version="0.3.0", lifespan=lifespan)
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

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        import logging
        logging.getLogger("stock_god").exception("Unhandled API error: %s", request.url.path, exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "服务暂时无法完成请求，变更已回滚。请稍后重试并查看服务日志。"})

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
                    "reflections": [{"id": r.id, "plan": r.plan, "review": r.review, "account_id": r.account_id, "created_at": iso_time(r.created_at)} for r in s.scalars(select(Reflection).where(Reflection.player_id == request.state.player_id).order_by(Reflection.created_at.desc()))]}

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

    @app.get("/api/courses/{lesson_id}")
    def get_course(request: Request, lesson_id: str):
        with owned_session(factory, request.state.player_id) as s:
            return course_detail(s, lesson_id)

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

    @app.get("/api/accounts/{mode}/bars/{symbol}")
    def bars(request: Request, mode: str, symbol: str):
        from stock_god.trading.engine import get_account
        if symbol not in PROVIDER.names:
            raise HTTPException(404, "没有这只教学股票。")
        with owned_session(factory, request.state.player_id) as s:
            a = get_account(s, mode)
            return PROVIDER.visible(symbol, a.day)

    @app.post("/api/accounts/{mode}/orders")
    def submit_order(request: Request, mode: str, body: OrderBody, idempotency_key: str = Header(min_length=8, max_length=128)):
        return mutate(request.state.player_id, "order:" + mode, idempotency_key, body.model_dump(mode="json"), lambda s: create_order(s, mode, body))

    @app.post("/api/accounts/{mode}/orders/{order_id}/cancel")
    def cancel_order(request: Request, mode: str, order_id: str, idempotency_key: str = Header(min_length=8, max_length=128)):
        return mutate(request.state.player_id, "cancel:" + mode + ":" + order_id, idempotency_key, {}, lambda s: cancel(s, mode, order_id))

    @app.post("/api/accounts/{mode}/advance")
    def advance_day(request: Request, mode: str, idempotency_key: str = Header(min_length=8, max_length=128)):
        return mutate(request.state.player_id, "advance:" + mode, idempotency_key, {}, lambda s: advance(s, mode))

    @app.post("/api/reflections")
    def reflect(request: Request, body: ReflectionBody, idempotency_key: str = Header(min_length=8, max_length=128)):
        def save(s):
            from stock_god.trading.engine import get_account
            r = Reflection(id=str(uuid4()), player_id=request.state.player_id, plan=body.plan, review=body.review, account_id=get_account(s, body.account_id).id)
            s.add(r)
            return {"id": r.id, "message": "计划和复盘已保存到学习档案。"}
        return mutate(request.state.player_id, "reflection", idempotency_key, body.model_dump(), save)

    @app.get("/api/experiments")
    def experiments(request: Request):
        with owned_session(factory, request.state.player_id) as s:
            return [job_view(j) for j in s.scalars(select(Job).where(Job.player_id == request.state.player_id).order_by(Job.created_at.desc()).limit(30))]

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
        question = body.question
        if any(word in question for word in ("推荐", "明天", "预测", "涨停", "买哪")):
            answer = "这里的教练只帮助你理解课程和模拟规则。教学数据不能用来预测真实股票。可以问我如何查看资金、理解费用或解释订单状态。"
        elif any(word in question for word in ("不成交", "没成交", "委托", "下单", "订单")):
            answer = "提交订单后先冻结资金或持仓，订单显示“待处理”。推进下一教学日才按开盘参考价检查限价；不满足价格条件或停牌时不会成交。请打开订单结果查看具体原因。"
        elif any(word in question for word in ("费用", "成本", "佣金")):
            answer = "教学费用由佣金、过户费和卖出时的印花税构成。佣金按成交金额的 0.03% 估算、每笔至少 5 元，这是教学假设。每笔成交都会列出实际扣除的费用。"
        elif any(word in question for word in ("卖", "持仓", "T+1")):
            answer = "总持仓包含今天刚买入的股票；可卖数量还要扣除当日买入和待处理卖单冻结的数量。本场景当日买入，下一教学日才可卖出。"
        elif "例" in question:
            answer = "换个例子：账户现金 30,000 元，待处理买单冻结 5,000 元，可用资金就是 25,000 元。撤销这张待处理买单后，5,000 元会释放，现金总额没有因此增加。"
        else:
            answer = detail["goal"] + " " + detail["practice"]
        return {"answer": answer, "source": detail["title"], "kind": "预设教学讲解"}

    @app.get("/api/export")
    def export(request: Request):
        # Human-readable portable audit export. Full restoration uses DB backup.
        with owned_session(factory, request.state.player_id) as s:
            rows = {}
            account_ids = select(Account.id).where(Account.player_id == request.state.player_id)
            for model in (Player, Account, Progress, Reward, Attempt, Reflection, ReviewItem, ReviewAttempt, Job, Order, Position, Ledger):
                table = model.__table__
                if model is Player:
                    statement = select(table.c.id, table.c.username, table.c.name, table.c.xp, table.c.onboarded, table.c.reduced_motion, table.c.guide_step, table.c.guide_status).where(table.c.id == request.state.player_id)
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
