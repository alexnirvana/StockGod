from decimal import Decimal
from stock_god.research.backtest import run_backtest
from stock_god.adapters.data import PROVIDER, RULES
from stock_god.trading.engine import fee


def params():
    return {"short_window": 5, "long_window": 15, "allocation": 30, "data_version": PROVIDER.version,
            "strategy_version": "sma-v1", "rule_version": RULES["version"]}


def test_reproducible_backtest_and_real_costs():
    first = run_backtest(params())
    assert first == run_backtest(params())
    assert first["trade_count"] > 0
    assert Decimal(first["fees"]) == sum(Decimal(t["fees"]) for t in first["trades"])
    assert first["curve"][0]["day"] == 15
    assert Decimal(first["max_drawdown"]) >= 0


def test_signal_cannot_read_same_day_close(monkeypatch):
    expected = run_backtest(params())["trades"][0]
    original = PROVIDER.bar
    def changed(symbol, day):
        bar = dict(original(symbol, day))
        if day == expected["day"]:
            bar["close"] = Decimal("0.01")
        return bar
    monkeypatch.setattr(PROVIDER, "bar", changed)
    assert run_backtest(params())["trades"][0] == expected


def test_minimum_fee_and_seller_tax():
    assert fee(Decimal("1000"), "buy") == Decimal("5.01")
    assert fee(Decimal("1000"), "sell") == Decimal("5.51")

