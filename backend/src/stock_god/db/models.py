from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.mysql import DATETIME as MySQLDateTime

REVIEW_TIME = DateTime(timezone=True).with_variant(MySQLDateTime(fsp=6), 'mysql')


def now():
    return datetime.now(timezone.utc)


def iso_time(value):
    # SQLite returns naive datetimes even for timezone=True; stored values are UTC.
    return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


class Base(DeclarativeBase):
    pass


class Player(Base):
    __tablename__ = "players"
    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    username: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guide_step: Mapped[int] = mapped_column(Integer, default=0)
    guide_status: Mapped[str] = mapped_column(String(16), default="pending")
    locale: Mapped[str] = mapped_column(String(16), default="zh-CN")
    name: Mapped[str] = mapped_column(String(30), default="投资小白")
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    reduced_motion: Mapped[bool] = mapped_column(Boolean, default=False)
    xp: Mapped[int] = mapped_column(Integer, default=0)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    player_id: Mapped[str] = mapped_column(String(191), index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ListeningProgress(Base):
    __tablename__ = 'listening_progress'
    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    player_id: Mapped[str] = mapped_column(String(191), index=True)
    lesson_id: Mapped[str] = mapped_column(String(191))
    locale: Mapped[str] = mapped_column(String(16))
    audio_version: Mapped[str] = mapped_column(String(64))
    position_ms: Mapped[int] = mapped_column(Integer, default=0)
    playback_rate: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal('1'))
    revision: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(REVIEW_TIME, default=now)


class AuthThrottle(Base):
    __tablename__ = "auth_throttles"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    hits: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("player_id", "mode", name="uq_accounts_player_mode"),)
    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    player_id: Mapped[str] = mapped_column(String(191))
    mode: Mapped[str] = mapped_column(String(191))
    cash: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("100000"))
    frozen_cash: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    day: Mapped[int] = mapped_column(Integer, default=19)
    rule_version: Mapped[str] = mapped_column(String(191), default="cn-mainboard-teaching-v1")


class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("account_id", "symbol"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(String(191), index=True)
    symbol: Mapped[str] = mapped_column(String(191))
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    sellable: Mapped[int] = mapped_column(Integer, default=0)
    frozen: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(191), index=True)
    symbol: Mapped[str] = mapped_column(String(191))
    side: Mapped[str] = mapped_column(String(191))
    quantity: Mapped[int] = mapped_column(Integer)
    limit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    reserved: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(191), default="pending")
    reason: Mapped[str] = mapped_column(Text)
    created_day: Mapped[int] = mapped_column(Integer)
    filled_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fill_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    fees: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Ledger(Base):
    __tablename__ = "ledger"
    __table_args__ = (UniqueConstraint("account_id", "source"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(String(191), index=True)
    source: Mapped[str] = mapped_column(String(191))
    kind: Mapped[str] = mapped_column(String(191))
    cash_delta: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    quantity_delta: Mapped[int] = mapped_column(Integer, default=0)
    symbol: Mapped[str | None] = mapped_column(String(191), nullable=True)
    day: Mapped[int] = mapped_column(Integer)
    rule_version: Mapped[str] = mapped_column(String(191), default="cn-mainboard-teaching-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Progress(Base):
    __tablename__ = "progress"
    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    player_id: Mapped[str] = mapped_column(String(191))
    lesson_id: Mapped[str] = mapped_column(String(191))
    version: Mapped[int] = mapped_column(Integer, default=1)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    review_due: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_score: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Reward(Base):
    __tablename__ = "rewards"
    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    player_id: Mapped[str] = mapped_column(String(191))
    lesson_id: Mapped[str] = mapped_column(String(191))
    xp: Mapped[int] = mapped_column(Integer)
    badge: Mapped[str] = mapped_column(String(191))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    lesson_id: Mapped[str] = mapped_column(String(191))
    player_id: Mapped[str] = mapped_column(String(191))
    answers: Mapped[list] = mapped_column(JSON)
    score: Mapped[int] = mapped_column(Integer)
    feedback: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ReviewItem(Base):
    __tablename__ = "review_items"
    __table_args__ = (
        UniqueConstraint("player_id", "lesson_id", "question_index", "content_version", name="uq_review_knowledge"),
        Index("ix_review_player_due", "player_id", "due_at"),
    )
    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    player_id: Mapped[str] = mapped_column(String(191))
    lesson_id: Mapped[str] = mapped_column(String(191))
    question_index: Mapped[int] = mapped_column(Integer)
    content_version: Mapped[int] = mapped_column(Integer, default=1)
    stage: Mapped[int] = mapped_column(Integer, default=0)
    mistakes: Mapped[int] = mapped_column(Integer, default=1)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    revision: Mapped[int] = mapped_column(Integer, default=0)
    due_at: Mapped[datetime | None] = mapped_column(REVIEW_TIME, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(REVIEW_TIME, default=now)


class ReviewAttempt(Base):
    __tablename__ = "review_attempts"
    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    player_id: Mapped[str] = mapped_column(String(191), index=True)
    review_id: Mapped[str] = mapped_column(String(191), index=True)
    variant: Mapped[int] = mapped_column(Integer)
    content_version: Mapped[int] = mapped_column(Integer)
    answer: Mapped[int] = mapped_column(Integer)
    passed: Mapped[bool] = mapped_column(Boolean)
    explanation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(REVIEW_TIME, default=now)


class Reflection(Base):
    __tablename__ = "reflections"
    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    player_id: Mapped[str] = mapped_column(String(191))
    account_id: Mapped[str] = mapped_column(String(191))
    plan: Mapped[str] = mapped_column(Text)
    review: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RequestRecord(Base):
    __tablename__ = "requests"
    player_id: Mapped[str] = mapped_column(String(191), index=True)
    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(191))
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(191), primary_key=True)
    player_id: Mapped[str] = mapped_column(String(191))
    kind: Mapped[str] = mapped_column(String(191), default="backtest")
    status: Mapped[str] = mapped_column(String(191), default="queued")
    params: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(191), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
