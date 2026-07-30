from datetime import datetime, timedelta
from decimal import Decimal
import unittest

from girp.domain import Candle
from girp.technical import ichimoku, pivot_points, rolling_support_resistance, supertrend


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


class IchimokuTests(unittest.TestCase):
    def test_insufficient_data_returns_none_fields(self) -> None:
        candles = make_candles([(10, 11, 9, 10)] * 5)
        result = ichimoku(candles)
        self.assertIsNone(result["tenkan_sen"])
        self.assertIsNone(result["kijun_sen"])
        self.assertIsNone(result["senkou_span_b"])

    def test_hand_verified_on_flat_series(self) -> None:
        # Flat high=11, low=9 for every bar -> midpoint always 10 for every lookback window.
        candles = make_candles([(10, 11, 9, 10)] * 60)
        result = ichimoku(candles)
        self.assertEqual(result["tenkan_sen"], Decimal("10"))
        self.assertEqual(result["kijun_sen"], Decimal("10"))
        self.assertEqual(result["senkou_span_a"], Decimal("10"))
        self.assertEqual(result["senkou_span_b"], Decimal("10"))
        self.assertEqual(result["chikou_span"], Decimal("10"))


class PivotPointsTests(unittest.TestCase):
    def test_needs_at_least_two_bars(self) -> None:
        candles = make_candles([(10, 11, 9, 10)])
        result = pivot_points(candles)
        self.assertIsNone(result["pivot"])

    def test_hand_verified_pivot(self) -> None:
        # Previous bar H=12, L=8, C=10 -> pivot = (12+8+10)/3 = 10
        # R1 = 2*10 - 8 = 12, S1 = 2*10 - 12 = 8
        # R2 = 10 + (12-8) = 14, S2 = 10 - (12-8) = 6
        candles = make_candles([(9, 12, 8, 10), (10, 10.5, 9.5, 10)])
        result = pivot_points(candles)
        self.assertEqual(result["pivot"], Decimal("10"))
        self.assertEqual(result["r1"], Decimal("12"))
        self.assertEqual(result["s1"], Decimal("8"))
        self.assertEqual(result["r2"], Decimal("14"))
        self.assertEqual(result["s2"], Decimal("6"))


class RollingSupportResistanceTests(unittest.TestCase):
    def test_insufficient_data_returns_none(self) -> None:
        candles = make_candles([(10, 11, 9, 10)] * 5)
        result = rolling_support_resistance(candles, period=20)
        self.assertIsNone(result["support"])
        self.assertIsNone(result["resistance"])

    def test_hand_verified_support_resistance(self) -> None:
        bars = [(10, 11, 9, 10)] * 19 + [(10, 20, 2, 10)]
        candles = make_candles(bars)
        result = rolling_support_resistance(candles, period=20)
        self.assertEqual(result["support"], Decimal("2"))
        self.assertEqual(result["resistance"], Decimal("20"))


class SupertrendTests(unittest.TestCase):
    def test_insufficient_data_returns_none(self) -> None:
        candles = make_candles([(10, 11, 9, 10)] * 5)
        result = supertrend(candles, period=10)
        self.assertIsNone(result["value"])
        self.assertIsNone(result["direction"])

    def test_strong_uptrend_flags_direction_up(self) -> None:
        candles = make_candles([(10 + i, 12 + i, 9 + i, 11 + i) for i in range(40)])
        result = supertrend(candles, period=10)
        self.assertIsNotNone(result["value"])
        self.assertEqual(result["direction"], Decimal("1"))

    def test_strong_downtrend_flags_direction_down(self) -> None:
        candles = make_candles([(50 - i, 52 - i, 49 - i, 48 - i) for i in range(40)])
        result = supertrend(candles, period=10)
        self.assertIsNotNone(result["value"])
        self.assertEqual(result["direction"], Decimal("-1"))


if __name__ == "__main__":
    unittest.main()
