from datetime import datetime, timedelta
from decimal import Decimal
import unittest

from girp.domain import Candle
from girp.technical import mfi, obv, vwap


def make_candles(bars: list[tuple[float, float, float, float, int]]) -> list[Candle]:
    """bars: list of (open, high, low, close, volume)."""
    return [
        Candle(
            symbol="ABC",
            timestamp=datetime(2024, 1, 1) + timedelta(days=index),
            open=Decimal(str(o)),
            high=Decimal(str(h)),
            low=Decimal(str(l)),
            close=Decimal(str(c)),
            volume=v,
        )
        for index, (o, h, l, c, v) in enumerate(bars)
    ]


class ObvTests(unittest.TestCase):
    def test_empty_returns_none(self) -> None:
        self.assertIsNone(obv([]))

    def test_hand_verified_obv(self) -> None:
        # Day1 close 10 (base, ignored). Day2 up (close 12) -> +200. Day3 down (close 9) -> -150.
        # Day4 flat (close 9) -> +0. Running total: 200 - 150 + 0 = 50.
        candles = make_candles(
            [
                (10, 10, 10, 10, 100),
                (10, 12, 10, 12, 200),
                (12, 12, 9, 9, 150),
                (9, 9, 9, 9, 300),
            ]
        )
        self.assertEqual(obv(candles), Decimal("50"))


class VwapTests(unittest.TestCase):
    def test_empty_returns_none(self) -> None:
        self.assertIsNone(vwap([]))

    def test_hand_verified_vwap(self) -> None:
        # Bar 1: typical price (10+8+9)/3 = 9, volume 100 -> value 900
        # Bar 2: typical price (14+12+13)/3 = 13, volume 300 -> value 3900
        # VWAP = (900 + 3900) / (100 + 300) = 4800 / 400 = 12
        candles = make_candles(
            [
                (9, 10, 8, 9, 100),
                (13, 14, 12, 13, 300),
            ]
        )
        self.assertEqual(vwap(candles), Decimal("12"))


class MfiTests(unittest.TestCase):
    def test_insufficient_data_returns_none(self) -> None:
        candles = make_candles([(10, 11, 9, 10, 100)] * 5)
        self.assertIsNone(mfi(candles, period=14))

    def test_all_up_days_yields_100(self) -> None:
        candles = make_candles([(10 + i, 11 + i, 9 + i, 10 + i, 100) for i in range(20)])
        self.assertEqual(mfi(candles, period=14), Decimal("100"))

    def test_all_down_days_yields_low_value(self) -> None:
        candles = make_candles([(30 - i, 31 - i, 29 - i, 30 - i, 100) for i in range(20)])
        result = mfi(candles, period=14)
        self.assertLess(result, Decimal("20"))


if __name__ == "__main__":
    unittest.main()
