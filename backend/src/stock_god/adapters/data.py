import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Protocol

CONTENT = Path(__file__).resolve().parents[4] / "content"
RULES = json.loads((CONTENT / "scenarios" / "rules.json").read_text(encoding="utf-8"))


class DataProvider(Protocol):
    version: str
    def bar(self, symbol: str, day: int): ...
    def visible(self, symbol: str, day: int): ...


class TeachingProvider:
    names = {"SG001": "星河科技", "SG002": "远航制造"}

    def __init__(self):
        raw = (CONTENT / "scenarios" / "teaching.json").read_bytes()
        self.version = "teaching-v1-" + hashlib.sha256(raw).hexdigest()[:12]
        self.data = json.loads(raw)
        self.last_day = len(self.data["SG001"]) - 1

    def bar(self, symbol, day):
        if symbol not in self.data or day < 0 or day > self.last_day:
            return None
        raw = self.data[symbol][day]
        return {**raw, **{k: Decimal(raw[k]) for k in ("open", "close", "high", "low")}}

    def visible(self, symbol, day):
        return self.data[symbol][:day + 1]

    def quote(self, symbol, day):
        bar, previous = self.bar(symbol, day), self.bar(symbol, max(day - 1, 0))
        change = (bar["close"] - previous["close"]) / previous["close"] * 100
        return {"symbol": symbol, "name": self.names[symbol], "price": str(bar["close"]),
                "change": str(change.quantize(Decimal("0.01"))), "volume": bar["volume"],
                "suspended": bar["suspended"]}


PROVIDER = TeachingProvider()

