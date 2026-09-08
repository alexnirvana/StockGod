import hashlib
import os
import re
import secrets
from datetime import timedelta, timezone
from uuid import uuid4
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from stock_god.db.models import AuthSession, AuthThrottle, Player, now
from stock_god.db.session import create_accounts, transaction

SESSION_COOKIE = 'stockgod_session'
CSRF_COOKIE = 'stockgod_csrf'
PASSWORDS = PasswordHash.recommended()
DUMMY_HASH = PASSWORDS.hash('timing-placeholder-not-an-account')


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class Credentials(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=10, max_length=128)
    locale: Literal['zh-CN', 'en'] = 'zh-CN'

    @field_validator('username')
    @classmethod
    def username_format(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[a-z0-9_]{3,32}', value):
            raise ValueError('用户名为 3–32 位英文字母、数字或下划线。')
        return value


def public_player(player):
    return {'id': player.id, 'username': player.username, 'name': player.name,
            'guide_step': player.guide_step, 'guide_status': player.guide_status, 'locale': player.locale}


def throttle(factory, request, action, username):
    # Persist counters across API restarts; account and IP counters share no secrets.
    ip = request.client.host if request.client else 'unknown'
    if os.getenv('TRUST_PROXY', 'false').lower() == 'true':
        ip = request.headers.get('x-real-ip', ip)
    for key, limit in ((f'{action}:ip:{ip}', 60), (f'{action}:user:{username}', 12)):
        blocked = False
        with transaction(factory) as s:
            identifier = digest(key)
            # The savepoint handles simultaneous first attempts without aborting the transaction.
            try:
                with s.begin_nested():
                    s.add(AuthThrottle(id=identifier, hits=0, window_start=now()))
                    s.flush()
            except IntegrityError:
                pass
            row = s.scalar(select(AuthThrottle).where(AuthThrottle.id == identifier).with_for_update())
            if now() - utc(row.window_start) >= timedelta(minutes=15):
                row.hits, row.window_start = 0, now()
            blocked = row.hits >= limit
            row.hits += 1
        if blocked:
            raise HTTPException(429, '尝试过于频繁，请 15 分钟后再试。', headers={'Retry-After': '900'})


def new_session(s, player_id, old_token=None):
    if old_token:
        s.execute(delete(AuthSession).where(AuthSession.id == digest(old_token)))
    s.execute(delete(AuthSession).where(AuthSession.expires_at < now()))
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    s.add(AuthSession(id=digest(token), player_id=player_id, csrf_hash=digest(csrf), expires_at=now() + timedelta(days=7)))
    return token, csrf


def set_cookies(response, tokens):
    secure = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
    for name, value, http_only in ((SESSION_COOKIE, tokens[0], True), (CSRF_COOKIE, tokens[1], False)):
        response.set_cookie(name, value, max_age=7 * 86400, httponly=http_only, secure=secure, samesite='lax', path='/')


def resolve_session(factory, request):
    token = request.cookies.get(SESSION_COOKIE, '')
    if len(token) < 32 or len(token) > 100:
        return None
    with factory() as s:
        auth = s.get(AuthSession, digest(token))
        if not auth or utc(auth.expires_at) <= now():
            return None
        player = s.get(Player, auth.player_id)
        if not player or not player.username:
            return None
        return auth.player_id, auth.csrf_hash


def auth_router(factory):
    router = APIRouter(prefix='/api/auth')

    @router.post('/register', status_code=201)
    def register(body: Credentials, request: Request, response: Response):
        throttle(factory, request, 'register', body.username)
        password_hash = PASSWORDS.hash(body.password)
        try:
            with transaction(factory) as s:
                player = Player(id=str(uuid4()), username=body.username, password_hash=password_hash,
                                name=body.username[:24], onboarded=True, guide_step=0, guide_status='pending', locale=body.locale)
                s.add(player)
                s.flush()
                create_accounts(s, player.id)
                tokens = new_session(s, player.id, request.cookies.get(SESSION_COOKIE))
                result = public_player(player)
        except IntegrityError:
            raise HTTPException(409, '这个用户名已被使用，请换一个用户名。')
        set_cookies(response, tokens)
        return {'user': result}

    @router.post('/login')
    def login(body: Credentials, request: Request, response: Response):
        throttle(factory, request, 'login', body.username)
        with factory() as s:
            player = s.scalar(select(Player).where(Player.username == body.username))
            valid = PASSWORDS.verify(body.password, player.password_hash if player and player.password_hash else DUMMY_HASH)
            if not valid or not player:
                raise HTTPException(401, '用户名或密码不正确。')
            player_id = player.id
        with transaction(factory, player_id) as s:
            player = s.get(Player, player_id)
            tokens = new_session(s, player_id, request.cookies.get(SESSION_COOKIE))
            result = public_player(player)
        set_cookies(response, tokens)
        return {'user': result}

    @router.get('/me')
    def me(request: Request):
        with factory() as s:
            return {'user': public_player(s.get(Player, request.state.player_id))}

    @router.post('/logout')
    def logout(request: Request, response: Response):
        with transaction(factory, request.state.player_id) as s:
            s.execute(delete(AuthSession).where(AuthSession.id == digest(request.cookies[SESSION_COOKIE])))
        response.delete_cookie(SESSION_COOKIE, path='/')
        response.delete_cookie(CSRF_COOKIE, path='/')
        return {'message': '已退出登录。'}

    return router
