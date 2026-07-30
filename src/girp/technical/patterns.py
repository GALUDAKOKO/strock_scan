from __future__ import annotations

from decimal import Decimal

from girp.domain import Candle

# All pattern detectors return Decimal("1") / Decimal("0") flags (not Python bools) so
# they compare cleanly against numeric literals in the Formula DSL, e.g. `doji > 0`.

_TRUE = Decimal("1")
_FALSE = Decimal("0")


def _body(candle: Candle) -> Decimal:
    return abs(candle.close - candle.open)


def _range(candle: Candle) -> Decimal:
    return candle.high - candle.low


def _upper_wick(candle: Candle) -> Decimal:
    return candle.high - max(candle.open, candle.close)


def _lower_wick(candle: Candle) -> Decimal:
    return min(candle.open, candle.close) - candle.low


def doji(candle: Candle, body_threshold: Decimal = Decimal("0.1")) -> Decimal:
    """Body is a small fraction of the bar's total range."""
    total_range = _range(candle)
    if total_range == 0:
        return _TRUE
    return _TRUE if (_body(candle) / total_range) <= body_threshold else _FALSE


def hammer(candle: Candle) -> Decimal:
    """Small body near the top of the range, long lower wick, little/no upper wick."""
    total_range = _range(candle)
    if total_range == 0:
        return _FALSE
    body = _body(candle)
    lower = _lower_wick(candle)
    upper = _upper_wick(candle)
    is_small_body = body <= total_range * Decimal("0.3")
    is_long_lower_wick = lower >= body * Decimal("2")
    is_short_upper_wick = upper <= total_range * Decimal("0.1")
    return _TRUE if (is_small_body and is_long_lower_wick and is_short_upper_wick) else _FALSE


def shooting_star(candle: Candle) -> Decimal:
    """Small body near the bottom of the range, long upper wick, little/no lower wick."""
    total_range = _range(candle)
    if total_range == 0:
        return _FALSE
    body = _body(candle)
    upper = _upper_wick(candle)
    lower = _lower_wick(candle)
    is_small_body = body <= total_range * Decimal("0.3")
    is_long_upper_wick = upper >= body * Decimal("2")
    is_short_lower_wick = lower <= total_range * Decimal("0.1")
    return _TRUE if (is_small_body and is_long_upper_wick and is_short_lower_wick) else _FALSE


def bullish_engulfing(previous: Candle, current: Candle) -> Decimal:
    """Previous bar bearish, current bar bullish, and current body engulfs the previous body."""
    previous_bearish = previous.close < previous.open
    current_bullish = current.close > current.open
    engulfs = current.open <= previous.close and current.close >= previous.open
    return _TRUE if (previous_bearish and current_bullish and engulfs) else _FALSE


def bearish_engulfing(previous: Candle, current: Candle) -> Decimal:
    """Previous bar bullish, current bar bearish, and current body engulfs the previous body."""
    previous_bullish = previous.close > previous.open
    current_bearish = current.close < current.open
    engulfs = current.open >= previous.close and current.close <= previous.open
    return _TRUE if (previous_bullish and current_bearish and engulfs) else _FALSE


def detect_patterns(candles: list[Candle]) -> dict[str, Decimal | None]:
    """Pattern flags for the latest bar (and, where needed, the bar before it)."""
    if not candles:
        return {
            "doji": None,
            "hammer": None,
            "shooting_star": None,
            "bullish_engulfing": None,
            "bearish_engulfing": None,
        }

    latest = candles[-1]
    result: dict[str, Decimal | None] = {
        "doji": doji(latest),
        "hammer": hammer(latest),
        "shooting_star": shooting_star(latest),
        "bullish_engulfing": None,
        "bearish_engulfing": None,
    }

    if len(candles) >= 2:
        previous = candles[-2]
        result["bullish_engulfing"] = bullish_engulfing(previous, latest)
        result["bearish_engulfing"] = bearish_engulfing(previous, latest)

    return result
