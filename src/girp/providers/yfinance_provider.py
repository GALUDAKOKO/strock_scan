from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from girp.domain import Asset, Candle, FinancialStatement, ProviderInfo


class YFinanceProvider:
    name = "yfinance"

    def __init__(self) -> None:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError(
                "yfinance is not installed. Install requirements.txt to use YFinanceProvider."
            ) from exc
        self._yf = yf

    def refresh(self, symbol: str) -> None:
        ticker = self._yf.Ticker(symbol)
        _ = ticker.fast_info

    def get_history(
        self,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
    ) -> list[Candle]:
        ticker = self._yf.Ticker(symbol)
        frame = ticker.history(start=start, end=end, interval=interval, auto_adjust=False)
        candles: list[Candle] = []
        for index, row in frame.iterrows():
            timestamp = index.to_pydatetime()
            candles.append(
                Candle(
                    symbol=symbol.upper(),
                    timestamp=timestamp,
                    open=_decimal(row["Open"]),
                    high=_decimal(row["High"]),
                    low=_decimal(row["Low"]),
                    close=_decimal(row["Close"]),
                    adjusted_close=_decimal(row.get("Adj Close")),
                    volume=int(row.get("Volume") or 0),
                )
            )
        return candles

    def get_financials(self, symbol: str) -> list[FinancialStatement]:
        ticker = self._yf.Ticker(symbol)
        statements: list[FinancialStatement] = []
        frame_sets = (
            (
                "annual",
                (ticker.financials, ticker.balance_sheet, ticker.cashflow),
            ),
            (
                "quarterly",
                (ticker.quarterly_financials, ticker.quarterly_balance_sheet, ticker.quarterly_cashflow),
            ),
        )
        for period, frames in frame_sets:
            columns: dict[Any, dict[str, Any]] = {}
            for frame in frames:
                if frame is None or frame.empty:
                    continue
                for column in frame.columns:
                    bucket = columns.setdefault(column, {})
                    for metric in frame.index:
                        bucket[str(metric)] = _json_value(frame.loc[metric, column])
            for column, metrics in columns.items():
                reported_at = column.date() if hasattr(column, "date") else None
                statements.append(
                    FinancialStatement(
                        symbol=symbol.upper(),
                        period=period,
                        reported_at=reported_at,
                        metrics=metrics,
                    )
                )
        return statements

    def get_info(self, symbol: str) -> Asset:
        ticker = self._yf.Ticker(symbol)
        info: dict[str, Any] = ticker.info or {}
        return Asset(
            symbol=symbol.upper(),
            market=info.get("exchange"),
            name=info.get("shortName") or info.get("longName"),
            asset_type=info.get("quoteType", "equity").lower(),
            currency=info.get("currency"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            country=info.get("country"),
            exchange=info.get("fullExchangeName") or info.get("exchange"),
        )

    def get_snapshot(self, symbol: str) -> dict[str, Any]:
        """Best-effort quote/valuation snapshot pulled from ticker.info.

        Not part of the strict MarketDataProvider protocol; callers should use
        getattr/hasattr guards so providers that omit it degrade gracefully.
        """
        ticker = self._yf.Ticker(symbol)
        info: dict[str, Any] = ticker.info or {}
        return {
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "market_cap": info.get("marketCap"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "price_to_book": info.get("priceToBook"),
            "trailing_eps": info.get("trailingEps"),
            "book_value": info.get("bookValue"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "free_cashflow": info.get("freeCashflow"),
            "return_on_equity": info.get("returnOnEquity"),
            "return_on_assets": info.get("returnOnAssets"),
            "revenue_growth": info.get("revenueGrowth"),
            "profit_margins": info.get("profitMargins"),
            "debt_to_equity": info.get("debtToEquity"),
            "total_debt": info.get("totalDebt"),
            "total_cash": info.get("totalCash"),
        }

    def provider_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            supports_history=True,
            supports_financials=True,
            supports_info=True,
        )


def _decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _json_value(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, datetime):
        return value.isoformat()
    return value
