from datetime import datetime, timedelta
from decimal import Decimal
import unittest

from girp.domain import Candle
from girp.technical import cci, ema_series, macd


def make_candles(bars: list[tuple[float, float, float, float]]) -> list[Candle]:
    return [
        Candle(
            symbol="ABC",
            timestamp=datetime(2024, 1, 1) + timedelta(days=index),
            open=Decimal(str(o)),
            high=Decimal(str(h)),
            low=Decimal(str(l)),
            close=Decimal(str(c)),
            volume=1000,
        )
        for index, (o, h, l, c) in enumerate(bars)
    ]


class EmaSeriesTests(unittest.TestCase):
    def test_insufficient_data_returns_empty(self) -> None:
        self.assertEqual(ema_series([Decimal(1), Decimal(2)], period=5), [])

    def test_first_value_is_seed_sma(self) -> None:
        values = [Decimal(i) for i in range(1, 6)]  # 1..5
        series = ema_series(values, period=5)
        self.assertEqual(len(series), 1)
        self.assertEqual(series[0], Decimal("3"))  # SMA of 1..5


class MacdTests(unittest.TestCase):
    def test_insufficient_data_returns_none(self) -> None:
        values = [Decimal(i) for i in range(1, 10)]
        result = macd(values, fast_period=12, slow_period=26, signal_period=9)
        self.assertIsNone(result["macd"])
        self.assertIsNone(result["signal"])
        self.assertIsNone(result["histogram"])

    def test_flat_series_yields_zero_macd(self) -> None:
        # Constant closes -> both EMAs equal the constant -> MACD line is 0, histogram 0.
        values = [Decimal("50")] * 50
        result = macd(values, fast_period=12, slow_period=26, signal_period=9)
        self.assertEqual(result["macd"], Decimal("0"))
        self.assertEqual(result["signal"], Decimal("0"))
        self.assertEqual(result["histogram"], Decimal("0"))

    def test_uptrend_yields_positive_macd(self) -> None:
        values = [Decimal(i) for i in range(1, 60)]
        result = macd(values)
        self.assertGreater(result["macd"], Decimal("0"))


class CciTests(unittest.TestCase):
    def test_insufficient_data_returns_none(self) -> None:
        candles = make_candles([(10, 11, 9, 10)] * 5)
        self.assertIsNone(cci(candles, period=20))

    def test_flat_series_yields_zero(self) -> None:
        candles = make_candles([(10, 11, 9, 10)] * 20)
        self.assertEqual(cci(candles, period=20), Decimal("0"))

    def test_breakout_bar_yields_positive_cci(self) -> None:
        candles = make_candles([(10, 11, 9, 10)] * 19 + [(10, 20, 10, 20)])
        result = cci(candles, period=20)
        self.assertGreater(result, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
