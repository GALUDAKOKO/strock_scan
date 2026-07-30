from __future__ import annotations

from datetime import date
from typing import Protocol

from girp.domain import Asset, Candle, FinancialStatement, ProviderInfo


class MarketDataProvider(Protocol):
    """Provider contract from spec/provider_interface.md."""

    def refresh(self, symbol: str) -> None:
        """Refresh remote/local provider state for a symbol."""

    def get_history(
        self,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
    ) -> list[Candle]:
        """Return OHLCV candles."""

    def get_financials(self, symbol: str) -> list[FinancialStatement]:
        """Return financial statement metric payloads."""

    def get_info(self, symbol: str) -> Asset:
        """Return asset metadata."""

    def provider_info(self) -> ProviderInfo:
        """Return provider capabilities."""
