from decimal import Decimal
from stock_god.adapters.data import PROVIDER, RULES
from stock_god.trading.engine import fee, money

D = Decimal


def run_backtest(params):
    if params["data_version"] != PROVIDER.version or params["rule_version"] != RULES["version"] or params["strategy_version"] != "sma-v1":
        raise ValueError("数据或规则版本不一致，无法复现该实验。请创建新的实验。")
    short, long = params["short_window"], params["long_window"]
    cash, shares, total_fees = D("100000.00"), 0, D("0.00")
    curve, trades = [], []
    peak, worst = cash, D("0")
    initial_price = PROVIDER.bar("SG001", long)["open"]
    for day in range(long, PROVIDER.last_day + 1):
        # Signal uses strictly previous closes; execution sees only today's open.
        previous = [PROVIDER.bar("SG001", i)["close"] for i in range(day - long, day)]
        signal = sum(previous[-short:]) / short > sum(previous) / long
        bar = PROVIDER.bar("SG001", day)
        price = bar["open"]
        if signal and not shares and not bar["suspended"]:
            budget = cash * D(params["allocation"]) / 100
            quantity = int(budget / price / 100) * 100
            while quantity and price * quantity + fee(price * quantity, "buy") > budget:
                quantity -= 100
            if quantity:
                costs = fee(price * quantity, "buy")
                cash -= money(price * quantity + costs)
                shares += quantity
                total_fees += costs
                trades.append({"day": day, "side": "buy", "quantity": quantity, "price": str(price), "fees": str(costs)})
        elif not signal and shares and not bar["suspended"]:
            costs = fee(price * shares, "sell")
            cash += money(price * shares - costs)
            total_fees += costs
            trades.append({"day": day, "side": "sell", "quantity": shares, "price": str(price), "fees": str(costs)})
            shares = 0
        equity = money(cash + shares * bar["close"])
        peak = max(peak, equity)
        drawdown = (equity / peak - 1) * 100
        worst = min(worst, drawdown)
        benchmark = money(D("100000") * bar["close"] / initial_price)
        curve.append({"day": day, "equity": str(equity), "benchmark": str(benchmark), "drawdown": str(money(drawdown))})
    return {"total_return": str(money((D(curve[-1]["equity"]) / 100000 - 1) * 100)), "max_drawdown": str(money(-worst)),
            "fees": str(money(total_fees)), "trade_count": len(trades), "curve": curve, "trades": trades,
            "data_version": PROVIDER.version, "strategy_version": "sma-v1", "rule_version": RULES["version"],
            "matching": "previous-close-signal-next-open-v1",
            "notes": ["固定虚构教学数据，不代表真实历史证券表现。",
                      "信号仅使用前一日及更早收盘价，次日开盘估算执行；整手、只做多、零滑点。",
                      "策略计入教学费用；基准为同区间满仓买入持有、不计费用，用于解释比较口径差异。",
                      "期末未强制平仓，持仓按收盘价估值。未模拟盘中路径和部分成交。",
                      "最大回撤相对起始资金及此前净值高点计算。回测不证明未来收益。"]}

