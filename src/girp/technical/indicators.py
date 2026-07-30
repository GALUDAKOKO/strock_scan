from __future__ import annotations

from decimal import Decimal

from girp.domain import Candle
from girp.technical.oscillators import cci, macd
from girp.technical.patterns import detect_patterns
from girp.technical.trend import ichimoku, pivot_points, rolling_support_resistance, supertrend
from girp.technical.volatility import adx, atr, bollinger_bands
from girp.technical.volume import mfi, obv, vwap


def sma(values: list[Decimal], period: int) -> Decimal | None:
    if period <= 0:
        raise ValueError("period must be positive")
    if len(values) < period:
        return None
    window = values[-period:]
    return sum(window) / Decimal(period)


def ema(values: list[Decimal], period: int) -> Decimal | None:
    if period <= 0:
        raise ValueError("period must be positive")
    if len(values) < period:
        return None

    multiplier = Decimal(2) / Decimal(period + 1)
    current = sum(values[:period]) / Decimal(period)
    for value in values[period:]:
        current = (value - current) * multiplier + current
    return current


def rsi(values: list[Decimal], period: int = 14) -> Decimal | None:
    if period <= 0:
        raise ValueError("period must be positive")
    if len(values) <= period:
        return None

    gains: list[Decimal] = []
    losses: list[Decimal] = []
    for previous, current in zip(values, values[1:]):
        change = current - previous
        gains.append(max(change, Decimal("0")))
        losses.append(abs(min(change, Decimal("0"))))

    average_gain = sum(gains[:period]) / Decimal(period)
    average_loss = sum(losses[:period]) / Decimal(period)

    for gain, loss in zip(gains[period:], losses[period:]):
        average_gain = ((average_gain * Decimal(period - 1)) + gain) / Decimal(period)
        average_loss = ((average_loss * Decimal(period - 1)) + loss) / Decimal(period)

    if average_loss == 0:
        return Decimal("100")

    relative_strength = average_gain / average_loss
    return Decimal("100") - (Decimal("100") / (Decimal("1") + relative_strength))


def percent_distance(value: Decimal, baseline: Decimal | None) -> Decimal | None:
    if baseline in (None, Decimal("0")):
        return None
    return ((value - baseline) / baseline) * Decimal("100")


def momentum_score(close_vs_sma_20: Decimal | None, close_vs_ema_20: Decimal | None, rsi_14: Decimal | None) -> Decimal | None:
    if close_vs_sma_20 is None or close_vs_ema_20 is None or rsi_14 is None:
        return None
    rsi_balance = Decimal("100") - abs(Decimal("55") - rsi_14)
    return (close_vs_sma_20 * Decimal("0.4")) + (close_vs_ema_20 * Decimal("0.4")) + (rsi_balance * Decimal("0.2"))


def summarize_history(candles: list[Candle]) -> dict[str, Decimal | int | str | None]:
    if not candles:
        return {}

    ordered = sorted(candles, key=lambda candle: candle.timestamp)
    closes = [candle.close for candle in ordered]
    latest = ordered[-1]
    sma_20 = sma(closes, 20)
    ema_20 = ema(closes, 20)
    rsi_14 = rsi(closes, 14)
    close_vs_sma_20 = percent_distance(latest.close, sma_20)
    close_vs_ema_20 = percent_distance(latest.close, ema_20)

    atr_14 = atr(ordered, 14)
    bands = bollinger_bands(closes, 20)
    directional = adx(ordered, 14)
    macd_values = macd(closes)
    cci_20 = cci(ordered, 20)
    obv_value = obv(ordered)
    vwap_value = vwap(ordered)
    mfi_14 = mfi(ordered, 14)
    ichimoku_values = ichimoku(ordered)
    supertrend_values = supertrend(ordered)
    pivots = pivot_points(ordered)
    support_resistance = rolling_support_resistance(ordered, 20)
    patterns = detect_patterns(ordered)

    return {
        "symbol": latest.symbol,
        "timestamp": latest.timestamp.isoformat(),
        "close": latest.close,
        "volume": latest.volume,
        "sma_20": sma_20,
        "ema_20": ema_20,
        "rsi_14": rsi_14,
        "close_vs_sma_20": close_vs_sma_20,
        "close_vs_ema_20": close_vs_ema_20,
        "momentum_score": momentum_score(close_vs_sma_20, close_vs_ema_20, rsi_14),
        "atr_14": atr_14,
        "bollinger_middle_20": bands["middle"],
        "bollinger_upper_20": bands["upper"],
        "bollinger_lower_20": bands["lower"],
        "bollinger_percent_b_20": bands["percent_b"],
        "adx_14": directional["adx"],
        "plus_di_14": directional["plus_di"],
        "minus_di_14": directional["minus_di"],
        "macd": macd_values["macd"],
        "macd_signal": macd_values["signal"],
        "macd_histogram": macd_values["histogram"],
        "cci_20": cci_20,
        "obv": obv_value,
        "vwap": vwap_value,
        "mfi_14": mfi_14,
        "ichimoku_tenkan_sen": ichimoku_values["tenkan_sen"],
        "ichimoku_kijun_sen": ichimoku_values["kijun_sen"],
        "ichimoku_senkou_span_a": ichimoku_values["senkou_span_a"],
        "ichimoku_senkou_span_b": ichimoku_values["senkou_span_b"],
        "ichimoku_chikou_span": ichimoku_values["chikou_span"],
        "supertrend": supertrend_values["value"],
        "supertrend_direction": supertrend_values["direction"],
        "pivot": pivots["pivot"],
        "pivot_r1": pivots["r1"],
        "pivot_r2": pivots["r2"],
        "pivot_s1": pivots["s1"],
        "pivot_s2": pivots["s2"],
        "support_20": support_resistance["support"],
        "resistance_20": support_resistance["resistance"],
        "pattern_doji": patterns["doji"],
        "pattern_hammer": patterns["hammer"],
        "pattern_shooting_star": patterns["shooting_star"],
        "pattern_bullish_engulfing": patterns["bullish_engulfing"],
        "pattern_bearish_engulfing": patterns["bearish_engulfing"],
    }