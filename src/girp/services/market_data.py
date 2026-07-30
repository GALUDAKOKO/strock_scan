from __future__ import annotations

from datetime import date, datetime

from girp.domain import Asset, Candle, FinancialStatement
from girp.providers import MarketDataProvider
from girp.storage import SQLiteCache


class MarketDataService:
    def __init__(self, provider: MarketDataProvider, cache: SQLiteCache) -> None:
        self.provider = provider
        self.cache = cache

    def get_info(self, symbol: str, refresh: bool = False) -> Asset:
        if not refresh:
            cached = self.cache.get_asset(symbol)
            if cached is not None:
                return cached

        asset = self.provider.get_info(symbol)
        self.cache.upsert_asset(asset)
        self.cache.touch_symbol_update(symbol)
        return asset

    def get_last_updated(self, symbol: str) -> datetime | None:
        """When data for `symbol` was last pulled fresh from the provider."""
        return self.cache.get_symbol_update(symbol)

    def get_last_updated_many(self, symbols: list[str]) -> dict[str, datetime | None]:
        return self.cache.get_symbol_updates(symbols)

    def get_history(
        self,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
        refresh: bool = False,
    ) -> list[Candle]:
        if not refresh:
            cached = self.cache.get_candles(symbol, start=start, end=end)
            if cached:
                return cached

        candles = self.provider.get_history(symbol, start=start, end=end, interval=interval)
        self.cache.upsert_candles(candles)
        self.cache.touch_symbol_update(symbol)
        return candles

    def get_financials(self, symbol: str, refresh: bool = False) -> list[FinancialStatement]:
        if not refresh:
            cached = self.cache.get_financials(symbol)
            if cached:
                return cached

        statements = self.provider.get_financials(symbol)
        self.cache.upsert_financials(statements)
        self.cache.touch_symbol_update(symbol)
        return statements

    def get_snapshot(self, symbol: str) -> dict:
        """Best-effort quote/valuation snapshot (price, shares, ratios).

        Providers are not required to implement this. When unavailable the
        fundamental and valuation engines fall back to whatever they can
        derive from financial statements and price history alone.
        """
        getter = getattr(self.provider, "get_snapshot", None)
        if getter is None:
            return {}
        try:
            return getter(symbol) or {}
        except Exception:
            return {}
