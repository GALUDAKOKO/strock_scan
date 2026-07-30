from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class Market:
    code: str
    name: str
    timezone: str | None = None
    currency: str | None = None


@dataclass(frozen=True)
class Asset:
    symbol: str
    market: str | None = None
    name: str | None = None
    asset_type: str = "equity"
    currency: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    exchange: str | None = None

    @property
    def key(self) -> str:
        if self.market:
            return f"{self.market}:{self.symbol}".upper()
        return self.symbol.upper()


@dataclass(frozen=True)
class Candle:
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adjusted_close: Decimal | None = None


@dataclass(frozen=True)
class FinancialStatement:
    symbol: str
    period: str
    reported_at: date | None
    metrics: dict[str, Any]


@dataclass(frozen=True)
class ProviderInfo:
    name: str
    supports_history: bool
    supports_financials: bool
    supports_info: bool
    markets: tuple[str, ...] = ()


@dataclass(frozen=True)
class Watchlist:
    name: str
    symbols: tuple[str, ...]
    updated_at: datetime | None = None
