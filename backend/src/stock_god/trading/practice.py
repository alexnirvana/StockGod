"""Independent free-practice rounds. Mutations run under the player's transaction lock."""
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select

from stock_god.adapters.data import PROVIDER, RULES
from stock_god.db.models import Account, Ledger, Order, Reflection, iso_time, now
from stock_god.db.session import owner
from stock_god.trading.engine import account_detail, get_account, require_context


def start_round(session, body):
    current = get_account(session, 'free')
    require_context(current, body.expected_account_id, body.expected_day)
    pending = session.scalar(select(Order.id).where(Order.account_id == current.id, Order.status == 'pending').limit(1))
    if pending or current.frozen_cash:
        raise HTTPException(409, '请先撤销或处理本轮待处理订单，再开始新一轮练习。')
    current.archived_at = now()
    fresh = Account(id=str(uuid4()), player_id=owner(session), mode='free',
                    round_number=current.round_number + 1, rule_version=RULES['version'], data_version=PROVIDER.version)
    session.add(fresh)
    session.flush()
    session.add(Ledger(account_id=fresh.id, source='initial', kind='initial', cash_delta=100000, day=19, rule_version=fresh.rule_version))
    session.flush()
    return account_detail(session, fresh)


def history(session, before=None, limit=20):
    query = select(Account).where(Account.player_id == owner(session), Account.mode == 'free')
    if before is not None:
        query = query.where(Account.round_number < before)
    rows = session.scalars(query.order_by(Account.round_number.desc()).limit(limit + 1)).all()
    return {'items': [
        {'id': row.id, 'round_number': row.round_number, 'day': row.day,
         'created_at': iso_time(row.created_at) if row.created_at else None,
         'archived_at': iso_time(row.archived_at) if row.archived_at else None,
         'data_version': row.data_version, 'rule_version': row.rule_version}
        for row in rows[:limit]],
        'next_before': rows[limit - 1].round_number if len(rows) > limit else None}


def detail(session, account_id):
    account = session.scalar(select(Account).where(Account.id == account_id, Account.player_id == owner(session), Account.mode == 'free'))
    if account is None:
        raise HTTPException(404, '没有找到这个练习轮次。')
    result = account_detail(session, account)
    result['reflections'] = [
        {'id': row.id, 'plan': row.plan, 'review': row.review, 'created_at': iso_time(row.created_at)}
        for row in session.scalars(select(Reflection).where(Reflection.account_id == account.id, Reflection.player_id == owner(session)).order_by(Reflection.created_at.desc(), Reflection.id))]
    return result
