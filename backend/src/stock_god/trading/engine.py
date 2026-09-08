from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select

from stock_god.db.models import Account, Order, Position, Ledger, iso_time
from stock_god.adapters.data import PROVIDER, RULES
from stock_god.db.session import owner

D = Decimal
ZERO = D("0.00")


def money(value):
    return D(value).quantize(D("0.01"), rounding=ROUND_HALF_UP)


def fee(amount, side):
    commission = max(D(RULES["minimum_commission"]), money(amount * D(RULES["commission_rate"])))
    transfer = money(amount * D(RULES["transfer_rate"]))
    stamp = money(amount * D(RULES["stamp_rate"])) if side == "sell" else ZERO
    return money(commission + transfer + stamp)


def get_account(session, mode):
    account = session.scalar(select(Account).where(Account.player_id == owner(session), Account.mode == mode, Account.archived_at.is_(None)))
    if account is None or mode not in ("tutorial", "free"):
        raise HTTPException(404, "没有这个模拟账户。请选择教学沙盒或自由模拟。")
    return account


def require_context(account, expected_account_id=None, expected_day=None):
    # Old tabs must not apply their intentions to a replacement account or later day.
    if account.mode == 'free' or expected_account_id is not None or expected_day is not None:
        if expected_account_id != account.id or expected_day != account.day:
            raise HTTPException(409, '练习轮次或教学日已变化，请刷新账户后重新确认操作。')


def require_versions(account):
    if account.data_version != PROVIDER.version or account.rule_version != RULES['version']:
        raise HTTPException(503, '该轮次使用的数据或规则版本暂不可用，原始记录已保留。')


def position(session, account_id, symbol):
    return session.scalar(select(Position).where(Position.account_id == account_id, Position.symbol == symbol))


def order_view(o):
    return {"id": o.id, "symbol": o.symbol, "name": PROVIDER.names[o.symbol], "side": o.side, "quantity": o.quantity,
            "limit_price": str(o.limit_price), "status": o.status, "reason": o.reason, "created_day": o.created_day,
            "filled_day": o.filled_day, "fill_price": str(o.fill_price) if o.fill_price is not None else None,
            "fees": str(o.fees), "created_at": iso_time(o.created_at)}


def account_view(session, mode):
    a = get_account(session, mode)
    return account_detail(session, a)


def account_detail(session, a):
    require_versions(a)
    positions = session.scalars(select(Position).where(Position.account_id == a.id, Position.quantity > 0)).all()
    value = sum((PROVIDER.bar(p.symbol, a.day)["close"] * p.quantity for p in positions), ZERO)
    return {"id": a.id, "mode": a.mode, "round_number": a.round_number,
            "created_at": iso_time(a.created_at) if a.created_at else None,
            "archived_at": iso_time(a.archived_at) if a.archived_at else None,
            "day": a.day, "cash": str(money(a.cash)), "frozen_cash": str(money(a.frozen_cash)),
            "available_cash": str(money(a.cash - a.frozen_cash)), "position_value": str(money(value)), "total_assets": str(money(a.cash + value)),
            "rule_version": a.rule_version, "data_label": "教学示例", "data_version": a.data_version,
            "positions": [{"symbol": p.symbol, "name": PROVIDER.names[p.symbol], "quantity": p.quantity,
                           "sellable": p.sellable - p.frozen, "frozen": p.frozen, "cost": str(money(p.cost)),
                           "price": str(PROVIDER.bar(p.symbol, a.day)["close"])} for p in positions],
            "orders": [order_view(o) for o in session.scalars(select(Order).where(Order.account_id == a.id).order_by(Order.created_at.desc())).all()],
            "bars": PROVIDER.visible("SG001", a.day),
            "quotes": [PROVIDER.quote(symbol, a.day) for symbol in PROVIDER.names],
            "ledger": [{"id": row.id, "source": row.source, "kind": row.kind, "cash_delta": str(row.cash_delta),
                        "quantity_delta": row.quantity_delta, "symbol": row.symbol, "day": row.day, "rule_version": row.rule_version}
                       for row in session.scalars(select(Ledger).where(Ledger.account_id == a.id).order_by(Ledger.id)).all()]}


def create_order(session, mode, body):
    a = get_account(session, mode)
    require_context(a, body.expected_account_id, body.expected_day)
    require_versions(a)
    if a.day >= PROVIDER.last_day:
        raise HTTPException(409, "教学场景已结束，不能提交新订单。可查看记录或使用另一个练习账户。")
    bar = PROVIDER.bar(body.symbol, a.day)
    if bar["suspended"]:
        raise HTTPException(409, "该教学股票当前停牌，无法申报。请切换股票或推进场景。")
    price = body.limit_price
    lower, upper = money(bar["close"] * D("0.90")), money(bar["close"] * D("1.10"))
    if not lower <= price <= upper:
        raise HTTPException(409, f"限价超出下一教学日的允许范围 {lower}–{upper} 元，请调整价格。")
    reserve = ZERO
    if body.side == "buy":
        reserve = money(price * body.quantity + fee(price * body.quantity, "buy"))
        if reserve > a.cash - a.frozen_cash:
            raise HTTPException(409, "可用虚拟资金不足，已有委托会冻结资金。请减少数量或撤销待处理订单。")
        a.frozen_cash += reserve
    else:
        p = position(session, a.id, body.symbol)
        if p is None or body.quantity > p.sellable - p.frozen:
            raise HTTPException(409, "可卖数量不足。当日买入需到下一教学日才可卖出，待处理卖单也会冻结持仓。")
        p.frozen += body.quantity
    o = Order(id=str(uuid4()), account_id=a.id, symbol=body.symbol, side=body.side, quantity=body.quantity,
              limit_price=price, reserved=reserve, status="pending", created_day=a.day,
              reason="委托已受理，尚未成交。推进下一教学日后，按开盘参考价与限价处理。")
    session.add(o)
    session.flush()
    return order_view(o)


def release(session, a, o):
    if o.side == "buy":
        a.frozen_cash = money(a.frozen_cash - o.reserved)
    else:
        p = position(session, a.id, o.symbol)
        p.frozen -= o.quantity


def cancel(session, mode, order_id):
    a = get_account(session, mode)
    o = session.get(Order, order_id)
    if o is None or o.account_id != a.id:
        raise HTTPException(404, "订单不存在于当前账户。")
    if o.status == "cancelled":
        return order_view(o)
    if o.status != "pending":
        raise HTTPException(409, "订单已处理，不能撤销。请查看订单结果。")
    release(session, a, o)
    o.status = "cancelled"
    o.reason = "撤单成功，冻结的资金或持仓已释放。"
    session.flush()
    return order_view(o)


def advance(session, mode, expected_account_id=None, expected_day=None):
    a = get_account(session, mode)
    require_context(a, expected_account_id, expected_day)
    require_versions(a)
    if a.day >= PROVIDER.last_day:
        raise HTTPException(409, "已到教学数据末尾，无法继续推进；你的账户和练习记录已保留。")
    next_day = a.day + 1
    pending = session.scalars(select(Order).where(Order.account_id == a.id, Order.status == "pending").order_by(Order.created_at, Order.id)).all()
    # Validate the entire next snapshot before mutating the clock or ledger.
    for symbol in PROVIDER.names:
        if PROVIDER.bar(symbol, next_day) is None:
            raise HTTPException(409, "下一教学日行情缺失，场景未推进，资金未结算。")
    for p in session.scalars(select(Position).where(Position.account_id == a.id)):
        p.sellable = p.quantity
    a.day = next_day
    for o in pending:
        bar = PROVIDER.bar(o.symbol, a.day)
        previous = PROVIDER.bar(o.symbol, a.day - 1)
        price = bar["open"]
        matched = price <= o.limit_price if o.side == "buy" else price >= o.limit_price
        one_price_limit = bar["high"] == bar["low"] and (price >= money(previous["close"] * D("1.10")) or price <= money(previous["close"] * D("0.90")))
        release(session, a, o)
        if bar["suspended"] or one_price_limit or not matched:
            o.status = "expired"
            o.reason = ("教学日停牌，订单未成交。" if bar["suspended"] else
                        "一字涨跌停，保守模型无法确认成交。" if one_price_limit else
                        "开盘参考价未达到委托限价。") + "本教学模型订单到期，冻结资金或持仓已释放。"
            continue
        amount = money(price * o.quantity)
        costs = fee(amount, o.side)
        p = position(session, a.id, o.symbol)
        if o.side == "buy":
            if p is None:
                p = Position(account_id=a.id, symbol=o.symbol, quantity=0, sellable=0, frozen=0, cost=ZERO)
                session.add(p)
            a.cash -= amount + costs
            p.quantity += o.quantity
            p.cost += amount + costs
            delta, qty = -amount - costs, o.quantity
        else:
            p.cost = money(p.cost * D(p.quantity - o.quantity) / D(p.quantity))
            p.quantity -= o.quantity
            p.sellable -= o.quantity
            a.cash += amount - costs
            delta, qty = amount - costs, -o.quantity
        o.status, o.fill_price, o.fees, o.filled_day = "filled", price, costs, a.day
        o.reason = f"日线估算成交：按下一教学日开盘参考价 {price} 元成交，费用 {costs} 元。无法还原真实排队与盘中路径。"
        session.add(Ledger(account_id=a.id, source=o.id, kind=o.side, cash_delta=delta, quantity_delta=qty, symbol=o.symbol, day=a.day))
    session.flush()
    return account_view(session, mode)
