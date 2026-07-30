from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from girp.formula import EvaluationError, ParseError, evaluate_formula, parse_formula
from girp.fundamental import compute_fundamentals
from girp.services import MarketDataService
from girp.technical import summarize_history


@dataclass(frozen=True)
class ScreeningResult:
    symbol: str
    passed: bool
    metrics: dict[str, Any]
    error: str | None = None


class ScreeningService:
    def __init__(self, market_data: MarketDataService) -> None:
        self.market_data = market_data

    def screen(
        self,
        symbols: list[str],
        formula: str,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
        refresh: bool = False,
        include_fundamentals: bool = False,
    ) -> list[ScreeningResult]:
        parsed = parse_formula(formula)
        results: list[ScreeningResult] = []

        for symbol in symbols:
            try:
                candles = self.market_data.get_history(
                    symbol,
                    start=start,
                    end=end,
                    interval=interval,
                    refresh=refresh,
                )
                metrics = summarize_history(candles)
                if include_fundamentals and metrics:
                    metrics = {
                        **metrics,
                        **self._fundamental_metrics(symbol, metrics.get("close"), refresh),
                    }
                if metrics:
                    metrics = {**metrics, **self._classification_metrics(symbol, refresh)}
                if not metrics:
                    results.append(
                        ScreeningResult(
                            symbol=symbol.upper(),
                            passed=False,
                            metrics={},
                            error="No price history available.",
                        )
                    )
                    continue

                passed = evaluate_formula(parsed, metrics)
                results.append(
                    ScreeningResult(
                        symbol=symbol.upper(),
                        passed=passed,
                        metrics=metrics,
                    )
                )
            except (EvaluationError, RuntimeError, ValueError) as exc:
                results.append(
                    ScreeningResult(
                        symbol=symbol.upper(),
                        passed=False,
                        metrics={},
                        error=str(exc),
                    )
                )

        return results

    def _fundamental_metrics(self, symbol: str, price: Any, refresh: bool) -> dict[str, Any]:
        try:
            statements = self.market_data.get_financials(symbol, refresh=refresh)
            snapshot = self.market_data.get_snapshot(symbol)
            return compute_fundamentals(statements, price=price, snapshot=snapshot)
        except (RuntimeError, ValueError):
            return {}

    def _classification_metrics(self, symbol: str, refresh: bool) -> dict[str, Any]:
        try:
            asset = self.market_data.get_info(symbol, refresh=refresh)
            return {
                "market": asset.market,
                "asset_type": asset.asset_type,
                "sector": asset.sector,
                "industry": asset.industry,
                "country": asset.country,
                "exchange": asset.exchange,
            }
        except (RuntimeError, ValueError):
            return {}


def validate_formula(formula: str) -> None:
    try:
        parse_formula(formula)
    except ParseError:
        raise