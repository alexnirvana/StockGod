"""Bind preserved anonymous records to a newly registered, unused account.

Administrator-only command; not exposed by HTTP. Sessions are revoked and the
user signs in again with their own password. No plaintext password is accepted.
"""
import argparse
from sqlalchemy import delete, select
from stock_god.db.models import Account, AuthSession, Attempt, Job, Ledger, Order, Player, Position, Progress, Reflection, RequestRecord, Reward
from stock_god.db.session import database, transaction
from stock_god.db.models import ReviewItem, ReviewAttempt, ListeningProgress


def claim_legacy(factory, username):
    with transaction(factory) as session:
        # A fixed lock order serializes concurrent administrator transfers.
        players = session.scalars(select(Player).order_by(Player.id).with_for_update()).all()
        legacy = next((p for p in players if p.id == 'local'), None)
        target = next((p for p in players if p.username == username.strip().lower()), None)
        if not legacy or legacy.username:
            raise ValueError('No unclaimed legacy account exists.')
        if not target or target.id == 'local':
            raise ValueError('Register your own account first, then provide its username.')
        accounts = session.scalars(select(Account).where(Account.player_id == target.id)).all()
        ids = [a.id for a in accounts]
        if target.xp or len(accounts) != 2 or any(a.round_number != 1 or a.archived_at or a.day != 19 or a.cash != 100000 or a.frozen_cash for a in accounts):
            raise ValueError('Target has activity; no records changed. Use an unused account.')
        for model in (Progress, Attempt, Reward, Reflection, ReviewItem, ReviewAttempt, ListeningProgress, Job):
            if session.scalar(select(model).where(model.player_id == target.id).limit(1)):
                raise ValueError('Target has learning activity; no records changed.')
        for model in (Order, Position):
            if session.scalar(select(model).where(model.account_id.in_(ids)).limit(1)):
                raise ValueError('Target has trading activity; no records changed.')
        if session.scalar(select(Ledger).where(Ledger.account_id.in_(ids), Ledger.kind != 'initial').limit(1)):
            raise ValueError('Target has ledger activity; no records changed.')
        username, password_hash = target.username, target.password_hash
        target.username = None
        session.flush()
        legacy.username, legacy.password_hash = username, password_hash
        legacy.reduced_motion = target.reduced_motion
        legacy.locale = target.locale
        legacy.guide_step, legacy.guide_status = 0, 'pending'
        for model in (AuthSession, RequestRecord):
            session.execute(delete(model).where(model.player_id == target.id))
        session.execute(delete(Ledger).where(Ledger.account_id.in_(ids)))
        session.execute(delete(Account).where(Account.player_id == target.id))
        session.delete(target)
    return 'Legacy learning and trading records bound. Sign in again with your existing password.'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('username')
    args = parser.parse_args()
    engine, factory = database()
    try:
        print(claim_legacy(factory, args.username))
    finally:
        engine.dispose()
