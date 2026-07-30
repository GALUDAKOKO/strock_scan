from __future__ import annotations

from decimal import Decimal

from girp.domain import Candle


def ema_series(values: list[Decimal], period: int) -> list[Decimal]:
    """Full EMA series aligned to the tail of `values` (first `period-1` inputs are consumed
    as the seed SMA, so the output has len(values) - period + 1 entries, oldest first)."""
    if period <= 0:
        raise ValueError("period must be positive")
    if len(values) < period:
        return []

    multiplier = Decimal(2) / Decimal(period + 1)
    series = [sum(values[:period]) / Decimal(period)]
    for value in values[period:]:
        series.append((value - series[-1]) * multiplier + series[-1])
    return series


def macd(
    values: list[Decimal],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> dict[str, Decimal | None]:
    """MACD line, signal line, and histogram from a list of closes (oldest first)."""
    fast = ema_series(values, fast_period)
    slow = ema_series(values, slow_period)
    if not fast or not slow:
        return {"macd": None, "signal": None, "histogram": None}

    # Align the two EMA series on their common tail (slow starts later since it needs more data).
    offset = len(fast) - len(slow)
    if offset < 0:
        return {"macd": None, "signal": None, "histogram": None}
    aligned_fast = fast[offset:]
    macd_line = [f - s for f, s in zip(aligned_fast, slow)]

    signal_series = ema_series(macd_line, signal_period)
    if not signal_series:
        return {"macd": macd_line[-1], "signal": None, "histogram": None}

    latest_macd = macd_line[-1]
    latest_signal = signal_series[-1]
    return {"macd": latest_macd, "signal": latest_signal, "histogram": latest_macd - latest_signal}


def cci(candles: list[Candle], period: int = 20) -> Decimal | None:
    """Commodity Channel Index from typical price ((H+L+C)/3) over `period` bars."""
    if period <= 0:
        raise ValueError("period must be positive")
    if len(candles) < period:
        return None

    window = candles[-period:]
    typical_prices = [(candle.high + candle.low + candle.close) / Decimal(3) for candle in window]
    mean_tp = sum(typical_prices) / Decimal(period)
    mean_deviation = sum(abs(tp - mean_tp) for tp in typical_prices) / Decimal(period)
    if mean_deviation == 0:
        return Decimal("0")
    return (typical_prices[-1] - mean_tp) / (Decimal("0.015") * mean_deviation)
