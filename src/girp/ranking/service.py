from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from girp.formula import EvaluationError, ParseError, evaluate_formula, parse_formula
from girp.fundamental import compute_fundamentals
from girp.ranking.composite import compute_composite_scores
from girp.services import MarketDataService
from girp.technical import summarize_history


@dataclass(frozen=True)
class RankingResult:
    rank: int | None
    symbol: str
    score: Decimal | int | float | None
    metrics: dict[str, Any]
    passed_filter: bool = True
    error: str | None = None


class RankingService:
    def __init__(self, market_data: MarketDataService) -> None:
        self.market_data = market_data

    def rank(
        self,
        symbols: list[str],
        sort_by: str = "momentum_score",
        descending: bool = True,
        formula: str | None = None,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
        refresh: bool = False,
        limit: int | None = None,
        include_fundamentals: bool = False,
    ) -> list[RankingResult]:
        parsed_formula = parse_formula(formula) if formula else None
        metrics_by_symbol: dict[str, dict[str, Any]] = {}
        errors: list[RankingResult] = []

        # Pass 1: fetch history + per-symbol metrics for everyone up front, so composite
        # scores can be computed cross-sectionally before filtering/sorting happens.
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
                    errors.append(RankingResult(None, symbol.upper(), None, {}, False, "No price history available."))
                    continue
                metrics_by_symbol[symbol.upper()] = metrics
            except (EvaluationError, RuntimeError, ValueError) as exc:
                errors.append(RankingResult(None, symbol.upper(), None, {}, False, str(exc)))

        composite_scores = compute_composite_scores(metrics_by_symbol)
        for symbol, scores in composite_scores.items():
            metrics_by_symbol[symbol] = {**metrics_by_symbol[symbol], **scores}

        # Pass 2: apply the optional filter formula and pick a sort score, now that every
        # metric (including composite scores) is available on every symbol's metrics dict.
        candidates: list[RankingResult] = []
        for symbol, metrics in metrics_by_symbol.items():
            try:
                passed_filter = True if parsed_formula is None else evaluate_formula(parsed_formula, metrics)
                score = metrics.get(sort_by)
                if not passed_filter:
                    candidates.append(RankingResult(None, symbol, _score_or_none(score), metrics, False))
                    continue
                if _score_or_none(score) is None:
                    errors.append(RankingResult(None, symbol, None, metrics, True, f"Metric '{sort_by}' is not rankable."))
                    continue
                candidates.append(RankingResult(None, symbol, score, metrics, True))
            except EvaluationError as exc:
                errors.append(RankingResult(None, symbol, None, metrics, False, str(exc)))

        passed = [candidate for candidate in candidates if candidate.passed_filter and candidate.error is None]
        filtered_out = [candidate for candidate in candidates if not candidate.passed_filter]
        ranked = sorted(passed, key=lambda item: _score_or_none(item.score) or Decimal("0"), reverse=descending)
        if limit is not None:
            ranked = ranked[:limit]

        ranked_with_numbers = [
            RankingResult(index, item.symbol, item.score, item.metrics, item.passed_filter, item.error)
            for index, item in enumerate(ranked, start=1)
        ]
        return ranked_with_numbers + filtered_out + errors

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


def _score_or_none(value: Any) -> Decimal | None:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value)
        except InvalidOperation:
            return None
    return None


def validate_rank_formula(formula: str | None) -> None:
    if formula:
        try:
            parse_formula(formula)
        except ParseError:
            raise
