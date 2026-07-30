from __future__ import annotations

from decimal import Decimal

from girp.domain import Candle
from girp.technical.volatility import atr_series


def _high_low_midpoint(candles: list[Candle], period: int) -> Decimal | None:
    if len(candles) < period:
        return None
    window = candles[-period:]
    highest = max(candle.high for candle in window)
    lowest = min(candle.low for candle in window)
    return (highest + lowest) / Decimal(2)


def ichimoku(
    candles: list[Candle],
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
) -> dict[str, Decimal | None]:
    """Ichimoku Cloud components as of the latest bar (no forward displacement)."""
    tenkan_sen = _high_low_midpoint(candles, tenkan_period)
    kijun_sen = _high_low_midpoint(candles, kijun_period)
    senkou_span_b = _high_low_midpoint(candles, senkou_b_period)
    senkou_span_a = (tenkan_sen + kijun_sen) / Decimal(2) if tenkan_sen is not None and kijun_sen is not None else None
    chikou_span = candles[-1].close if candles else None

    return {
        "tenkan_sen": tenkan_sen,
        "kijun_sen": kijun_sen,
        "senkou_span_a": senkou_span_a,
        "senkou_span_b": senkou_span_b,
        "chikou_span": chikou_span,
    }


def supertrend(
    candles: list[Candle], period: int = 10, multiplier: Decimal = Decimal("3")
) -> dict[str, Decimal | int | None]:
    """Supertrend line and direction (1 = uptrend, -1 = downtrend) as Formula-DSL-friendly flags."""
    atrs = atr_series(candles, period)
    if len(candles) <= period or all(value is None for value in atrs):
        return {"value": None, "direction": None}

    final_upper: Decimal | None = None
    final_lower: Decimal | None = None
    direction = 1
    trend_value: Decimal | None = None

    for index, candle in enumerate(candles):
        current_atr = atrs[index]
        if current_atr is None:
            continue

        mid = (candle.high + candle.low) / Decimal(2)
        basic_upper = mid + (multiplier * current_atr)
        basic_lower = mid - (multiplier * current_atr)

        if final_upper is None or final_lower is None:
            final_upper, final_lower = basic_upper, basic_lower
            trend_value = final_lower
            direction = 1
            continue

        previous_close = candles[index - 1].close
        final_upper = basic_upper if (basic_upper < final_upper or previous_close > final_upper) else final_upper
        final_lower = basic_lower if (basic_lower > final_lower or previous_close < final_lower) else final_lower

        if direction == 1 and candle.close < final_lower:
            direction = -1
        elif direction == -1 and candle.close > final_upper:
            direction = 1

        trend_value = final_lower if direction == 1 else final_upper

    return {"value": trend_value, "direction": Decimal(direction) if trend_value is not None else None}


def pivot_points(candles: list[Candle]) -> dict[str, Decimal | None]:
    """Classic floor pivot levels for the current session, derived from the prior bar's H/L/C."""
    if len(candles) < 2:
        return {"pivot": None, "r1": None, "r2": None, "s1": None, "s2": None}

    previous = candles[-2]
    pivot = (previous.high + previous.low + previous.close) / Decimal(3)
    r1 = (Decimal(2) * pivot) - previous.low
    s1 = (Decimal(2) * pivot) - previous.high
    r2 = pivot + (previous.high - previous.low)
    s2 = pivot - (previous.high - previous.low)

    return {"pivot": pivot, "r1": r1, "r2": r2, "s1": s1, "s2": s2}


def rolling_support_resistance(candles: list[Candle], period: int = 20) -> dict[str, Decimal | None]:
    """Simple rolling support/resistance: lowest low and highest high over the last `period` bars."""
    if len(candles) < period:
        return {"support": None, "resistance": None}
    window = candles[-period:]
    return {
        "support": min(candle.low for candle in window),
        "resistance": max(candle.high for candle in window),
    }
