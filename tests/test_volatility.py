from datetime import datetime, timedelta
from decimal import Decimal
import unittest

from girp.domain import Candle
from girp.technical import adx, atr, atr_series, bollinger_bands, true_range, true_range_series


def make_candles(bars: list[tuple[float, float, float, float]]) -> list[Candle]:
    """bars: list of (open, high, low, close)."""
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


class TrueRangeTests(unittest.TestCase):
    def test_first_bar_is_high_minus_low(self) -> None:
        self.assertEqual(true_range(None, Decimal("10"), Decimal("8")), Decimal("2"))

    def test_uses_previous_close_when_gap_up(self) -> None:
        # Gap up: previous close 10, today's low is 11 -> range vs prior close (11-10=1)
        # but high-low is bigger, so true range should be max of the three.
        self.assertEqual(true_range(Decimal("10"), Decimal("15"), Decimal("11")), Decimal("5"))

    def test_series_matches_hand_calculation(self) -> None:
        # Bars: (O,H,L,C)
        candles = make_candles(
            [
                (10, 12, 9, 11),   # first bar: TR = H-L = 3
                (11, 13, 10, 12),  # TR = max(3, |13-11|=2, |10-11|=1) = 3
                (12, 12, 8, 9),    # TR = max(4, |12-12|=0, |8-12|=4) = 4
            ]
        )
        self.assertEqual(true_range_series(candles), [Decimal("3"), Decimal("3"), Decimal("4")])


class AtrTests(unittest.TestCase):
    def test_insufficient_data_returns_none(self) -> None:
        candles = make_candles([(10, 11, 9, 10)] * 5)
        self.assertIsNone(atr(candles, period=14))

    def test_hand_verified_atr(self) -> None:
        # 15 bars of true range = 2 each (constant range), so ATR should settle at 2.
        candles = make_candles([(10, 12, 10, 11)] * 15)
        result = atr(candles, period=14)
        self.assertEqual(result, Decimal("2"))

    def test_atr_series_length_matches_candles(self) -> None:
        candles = make_candles([(10, 12, 10, 11)] * 20)
        series = atr_series(candles, period=14)
        self.assertEqual(len(series), 20)
        self.assertTrue(all(value is None for value in series[:14]))
        self.assertIsNotNone(series[14])


class BollingerBandsTests(unittest.TestCase):
    def test_insufficient_data_returns_none_fields(self) -> None:
        result = bollinger_bands([Decimal(i) for i in range(5)], period=20)
        self.assertIsNone(result["middle"])
        self.assertIsNone(result["upper"])
        self.assertIsNone(result["lower"])
        self.assertIsNone(result["percent_b"])

    def test_hand_verified_bands_on_constant_series(self) -> None:
        # Constant closes -> std dev 0 -> upper == lower == middle, %B undefined (0 width).
        values = [Decimal("10")] * 20
        result = bollinger_bands(values, period=20)
        self.assertEqual(result["middle"], Decimal("10"))
        self.assertEqual(result["upper"], Decimal("10"))
        self.assertEqual(result["lower"], Decimal("10"))
        self.assertIsNone(result["percent_b"])

    def test_hand_verified_bands_on_simple_series(self) -> None:
        # Closes 1..20 (mean 10.5). Population std dev of 1..20 is sqrt(33.25) ~= 5.766281.
        values = [Decimal(i) for i in range(1, 21)]
        result = bollinger_bands(values, period=20, num_std=Decimal("2"))
        self.assertEqual(result["middle"], Decimal("10.5"))
        expected_std = Decimal("33.25").sqrt()
        self.assertEqual(result["upper"], Decimal("10.5") + expected_std * 2)
        self.assertEqual(result["lower"], Decimal("10.5") - expected_std * 2)
        self.assertGreater(result["percent_b"], Decimal("0.9"))  # last close (20) near upper band


class AdxTests(unittest.TestCase):
    def test_insufficient_data_returns_none(self) -> None:
        candles = make_candles([(10, 11, 9, 10)] * 10)
        result = adx(candles, period=14)
        self.assertIsNone(result["adx"])
        self.assertIsNone(result["plus_di"])
        self.assertIsNone(result["minus_di"])

    def test_strong_uptrend_favors_plus_di(self) -> None:
        # Each bar makes a new, larger high with a rising low -> clean uptrend.
        candles = make_candles(
            [(10 + i, 12 + i, 9 + i, 11 + i) for i in range(40)]
        )
        result = adx(candles, period=14)
        self.assertIsNotNone(result["adx"])
        self.assertGreater(result["plus_di"], result["minus_di"])

    def test_strong_downtrend_favors_minus_di(self) -> None:
        candles = make_candles(
            [(50 - i, 52 - i, 49 - i, 51 - i) for i in range(40)]
        )
        result = adx(candles, period=14)
        self.assertIsNotNone(result["adx"])
        self.assertGreater(result["minus_di"], result["plus_di"])


if __name__ == "__main__":
    unittest.main()
