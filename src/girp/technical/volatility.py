from __future__ import annotations

from decimal import Decimal

from girp.domain import Candle


def true_range(previous_close: Decimal | None, high: Decimal, low: Decimal) -> Decimal:
    """True range for a single bar. Falls back to high-low when there is no prior close."""
    high_low = high - low
    if previous_close is None:
        return high_low
    return max(high_low, abs(high - previous_close), abs(low - previous_close))


def true_range_series(candles: list[Candle]) -> list[Decimal]:
    """True range for every bar in `candles` (must already be sorted ascending)."""
    ranges: list[Decimal] = []
    previous_close: Decimal | None = None
    for candle in candles:
        ranges.append(true_range(previous_close, candle.high, candle.low))
        previous_close = candle.close
    return ranges


def atr_series(candles: list[Candle], period: int = 14) -> list[Decimal | None]:
    """Wilder-smoothed ATR for every bar. First `period` entries are None."""
    if period <= 0:
        raise ValueError("period must be positive")
    ranges = true_range_series(candles)
    if len(ranges) <= period:
        return [None] * len(ranges)

    result: list[Decimal | None] = [None] * period
    current = sum(ranges[:period]) / Decimal(period)
    result.append(current)
    for tr in ranges[period + 1:]:
        current = ((current * Decimal(period - 1)) + tr) / Decimal(period)
        result.append(current)
    return result


def atr(candles: list[Candle], period: int = 14) -> Decimal | None:
    """Latest Wilder-smoothed Average True Range, or None if not enough bars."""
    series = atr_series(candles, period)
    return series[-1] if series else None


def bollinger_bands(
    values: list[Decimal], period: int = 20, num_std: Decimal = Decimal("2")
) -> dict[str, Decimal | None]:
    """Bollinger Bands (middle/upper/lower/%B) from the latest `period` closes."""
    if period <= 0:
        raise ValueError("period must be positive")
    if len(values) < period:
        return {"middle": None, "upper": None, "lower": None, "percent_b": None}

    window = values[-period:]
    middle = sum(window) / Decimal(period)
    variance = sum((value - middle) ** 2 for value in window) / Decimal(period)
    std_dev = variance.sqrt()
    upper = middle + (std_dev * num_std)
    lower = middle - (std_dev * num_std)

    band_width = upper - lower
    percent_b = ((values[-1] - lower) / band_width) if band_width != 0 else None

    return {"middle": middle, "upper": upper, "lower": lower, "percent_b": percent_b}


def _directional_movement(candles: list[Candle]) -> tuple[list[Decimal], list[Decimal]]:
    plus_dm: list[Decimal] = []
    minus_dm: list[Decimal] = []
    for previous, current in zip(candles, candles[1:]):
        up_move = current.high - previous.high
        down_move = previous.low - current.low
        plus = up_move if (up_move > down_move and up_move > 0) else Decimal("0")
        minus = down_move if (down_move > up_move and down_move > 0) else Decimal("0")
        plus_dm.append(plus)
        minus_dm.append(minus)
    return plus_dm, minus_dm


def _wilder_smooth(values: list[Decimal], period: int) -> list[Decimal]:
    """Wilder's smoothing, aligned so index 0 corresponds to the (period-1)-th input value."""
    if len(values) < period:
        return []
    smoothed = [sum(values[:period])]
    for value in values[period:]:
        smoothed.append(smoothed[-1] - (smoothed[-1] / Decimal(period)) + value)
    return smoothed


def adx(candles: list[Candle], period: int = 14) -> dict[str, Decimal | None]:
    """Average Directional Index with +DI/-DI. Needs roughly 2*period bars of history."""
    if period <= 0:
        raise ValueError("period must be positive")
    if len(candles) <= period * 2:
        return {"adx": None, "plus_di": None, "minus_di": None}

    ordered = candles
    trs = true_range_series(ordered)[1:]  # align with directional movement (drops first bar)
    plus_dm, minus_dm = _directional_movement(ordered)

    smoothed_tr = _wilder_smooth(trs, period)
    smoothed_plus_dm = _wilder_smooth(plus_dm, period)
    smoothed_minus_dm = _wilder_smooth(minus_dm, period)

    if not smoothed_tr or not smoothed_plus_dm or not smoothed_minus_dm:
        return {"adx": None, "plus_di": None, "minus_di": None}

    plus_di_series: list[Decimal] = []
    minus_di_series: list[Decimal] = []
    dx_series: list[Decimal] = []
    for tr_value, plus_value, minus_value in zip(smoothed_tr, smoothed_plus_dm, smoothed_minus_dm):
        if tr_value == 0:
            plus_di = Decimal("0")
            minus_di = Decimal("0")
        else:
            plus_di = (plus_value / tr_value) * Decimal("100")
            minus_di = (minus_value / tr_value) * Decimal("100")
        plus_di_series.append(plus_di)
        minus_di_series.append(minus_di)

        di_sum = plus_di + minus_di
        dx = (abs(plus_di - minus_di) / di_sum) * Decimal("100") if di_sum != 0 else Decimal("0")
        dx_series.append(dx)

    if len(dx_series) < period:
        return {"adx": None, "plus_di": plus_di_series[-1], "minus_di": minus_di_series[-1]}

    adx_value = sum(dx_series[:period]) / Decimal(period)
    for dx in dx_series[period:]:
        adx_value = ((adx_value * Decimal(period - 1)) + dx) / Decimal(period)

    return {
        "adx": adx_value,
        "plus_di": plus_di_series[-1],
        "minus_di": minus_di_series[-1],
    }
