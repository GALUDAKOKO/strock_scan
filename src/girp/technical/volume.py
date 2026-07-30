from __future__ import annotations

from decimal import Decimal

from girp.domain import Candle


def obv(candles: list[Candle]) -> Decimal | None:
    """On-Balance Volume: cumulative volume, added on up days and subtracted on down days."""
    if not candles:
        return None
    running = Decimal("0")
    for previous, current in zip(candles, candles[1:]):
        if current.close > previous.close:
            running += Decimal(current.volume)
        elif current.close < previous.close:
            running -= Decimal(current.volume)
    return running


def vwap(candles: list[Candle]) -> Decimal | None:
    """Volume-Weighted Average Price over the given bars (typical price weighted by volume)."""
    if not candles:
        return None
    total_volume = sum(Decimal(candle.volume) for candle in candles)
    if total_volume == 0:
        return None
    total_value = sum(
        ((candle.high + candle.low + candle.close) / Decimal(3)) * Decimal(candle.volume)
        for candle in candles
    )
    return total_value / total_volume


def mfi(candles: list[Candle], period: int = 14) -> Decimal | None:
    """Money Flow Index: RSI-like oscillator weighted by (typical price * volume)."""
    if period <= 0:
        raise ValueError("period must be positive")
    if len(candles) <= period:
        return None

    typical_prices = [(candle.high + candle.low + candle.close) / Decimal(3) for candle in candles]
    money_flows = [tp * Decimal(candle.volume) for tp, candle in zip(typical_prices, candles)]

    positive_flows: list[Decimal] = []
    negative_flows: list[Decimal] = []
    for i in range(1, len(typical_prices)):
        if typical_prices[i] > typical_prices[i - 1]:
            positive_flows.append(money_flows[i])
            negative_flows.append(Decimal("0"))
        elif typical_prices[i] < typical_prices[i - 1]:
            positive_flows.append(Decimal("0"))
            negative_flows.append(money_flows[i])
        else:
            positive_flows.append(Decimal("0"))
            negative_flows.append(Decimal("0"))

    window_positive = positive_flows[-period:]
    window_negative = negative_flows[-period:]
    positive_sum = sum(window_positive)
    negative_sum = sum(window_negative)

    if negative_sum == 0:
        return Decimal("100")

    money_ratio = positive_sum / negative_sum
    return Decimal("100") - (Decimal("100") / (Decimal("1") + money_ratio))
