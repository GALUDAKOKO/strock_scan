from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

# Each factor maps to True if a higher raw value is "better" for that category,
# False if a lower raw value is better (the percentile is inverted before averaging).
QUALITY_FACTORS: dict[str, bool] = {
    "roe": True,
    "roa": True,
    "roic": True,
    "net_margin": True,
    "current_ratio": True,
}
GROWTH_FACTORS: dict[str, bool] = {
    "revenue_growth": True,
    "asset_growth": True,
}
VALUE_FACTORS: dict[str, bool] = {
    "pe": False,
    "pbv": False,
}
MOMENTUM_FACTORS: dict[str, bool] = {
    "momentum_score": True,
    "close_vs_sma_20": True,
    "close_vs_ema_20": True,
}
# Risk factors are "bad when high", so a low raw value should score well (high percentile).
RISK_FACTORS: dict[str, bool] = {
    "debt_to_equity": False,
    "atr_pct": False,
}

CATEGORIES: dict[str, dict[str, bool]] = {
    "quality": QUALITY_FACTORS,
    "growth": GROWTH_FACTORS,
    "value": VALUE_FACTORS,
    "momentum": MOMENTUM_FACTORS,
    "risk": RISK_FACTORS,
}


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _percentile_ranks(values: dict[str, Decimal]) -> dict[str, Decimal]:
    """0-100 percentile rank per symbol, ties sharing the average rank."""
    if not values:
        return {}
    if len(values) == 1:
        only_symbol = next(iter(values))
        return {only_symbol: Decimal("50")}

    ordered = sorted(values.items(), key=lambda kv: kv[1])
    n = len(ordered)
    ranks: dict[str, Decimal] = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and ordered[j + 1][1] == ordered[i][1]:
            j += 1
        average_rank = Decimal(i + j) / Decimal(2)
        percentile = (average_rank / Decimal(n - 1)) * Decimal(100)
        for k in range(i, j + 1):
            ranks[ordered[k][0]] = percentile
        i = j + 1
    return ranks


def _category_score(
    metrics_by_symbol: dict[str, dict[str, Any]], factors: dict[str, bool]
) -> dict[str, Decimal | None]:
    factor_percentiles: dict[str, dict[str, Decimal]] = {}

    for factor, higher_is_better in factors.items():
        values: dict[str, Decimal] = {}
        for symbol, metrics in metrics_by_symbol.items():
            decimal_value = _to_decimal(metrics.get(factor))
            if decimal_value is not None:
                values[symbol] = decimal_value

        percentiles = _percentile_ranks(values)
        if not higher_is_better:
            percentiles = {symbol: Decimal(100) - value for symbol, value in percentiles.items()}
        factor_percentiles[factor] = percentiles

    scores: dict[str, Decimal | None] = {}
    for symbol in metrics_by_symbol:
        available = [
            factor_percentiles[factor][symbol]
            for factor in factors
            if symbol in factor_percentiles[factor]
        ]
        scores[symbol] = (sum(available) / Decimal(len(available))) if available else None
    return scores


def compute_composite_scores(metrics_by_symbol: dict[str, dict[str, Any]]) -> dict[str, dict[str, Decimal | None]]:
    """Cross-sectional Quality/Growth/Value/Momentum/Risk/Overall scores (0-100).

    Every score is computed relative to the other symbols in this same batch (percentile
    rank across whatever fundamentals/technical fields happen to be present), not against
    some fixed universe-wide benchmark. Categories with no usable factors for a symbol
    come back as None rather than a misleading default.
    """
    augmented: dict[str, dict[str, Any]] = {}
    for symbol, metrics in metrics_by_symbol.items():
        merged = dict(metrics)
        atr_14 = _to_decimal(metrics.get("atr_14"))
        close = _to_decimal(metrics.get("close"))
        if atr_14 is not None and close not in (None, Decimal("0")):
            merged["atr_pct"] = (atr_14 / close) * Decimal("100")
        augmented[symbol] = merged

    category_scores = {name: _category_score(augmented, factors) for name, factors in CATEGORIES.items()}

    result: dict[str, dict[str, Decimal | None]] = {}
    for symbol in metrics_by_symbol:
        per_symbol = {name: category_scores[name][symbol] for name in CATEGORIES}
        available = [value for value in per_symbol.values() if value is not None]
        overall = (sum(available) / Decimal(len(available))) if available else None
        result[symbol] = {
            "score_quality": per_symbol["quality"],
            "score_growth": per_symbol["growth"],
            "score_value": per_symbol["value"],
            "score_momentum": per_symbol["momentum"],
            "score_risk": per_symbol["risk"],
            "score_overall": overall,
        }
    return result
