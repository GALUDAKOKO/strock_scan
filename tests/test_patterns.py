from datetime import datetime
from decimal import Decimal
import unittest

from girp.domain import Candle
from girp.technical import bearish_engulfing, bullish_engulfing, detect_patterns, doji, hammer, shooting_star


def make_candle(o: float, h: float, l: float, c: float) -> Candle:
    return Candle(
        symbol="ABC",
        timestamp=datetime(2024, 1, 1),
        open=Decimal(str(o)),
        high=Decimal(str(h)),
        low=Decimal(str(l)),
        close=Decimal(str(c)),
        volume=1000,
    )


class DojiTests(unittest.TestCase):
    def test_detects_doji(self) -> None:
        # Body 0.1 vs range 10 -> 1% <= 10% threshold.
        candle = make_candle(10, 15, 5, 10.1)
        self.assertEqual(doji(candle), Decimal("1"))

    def test_rejects_large_body(self) -> None:
        candle = make_candle(5, 15, 5, 15)
        self.assertEqual(doji(candle), Decimal("0"))


class HammerTests(unittest.TestCase):
    def test_detects_hammer(self) -> None:
        # Range 5-15 (10). Body near top: open 13, close 14 (body=1, <=30% of 10).
        # Lower wick = 13-5=8 (>= 2*body=2). Upper wick = 15-14=1 (<=10% of 10=1).
        candle = make_candle(13, 15, 5, 14)
        self.assertEqual(hammer(candle), Decimal("1"))

    def test_rejects_non_hammer_shape(self) -> None:
        candle = make_candle(5, 15, 5, 15)
        self.assertEqual(hammer(candle), Decimal("0"))


class ShootingStarTests(unittest.TestCase):
    def test_detects_shooting_star(self) -> None:
        # Range 5-15 (10). Body near bottom: open 6, close 7 (body=1).
        # Upper wick = 15-7=8 (>=2). Lower wick = 6-5=1 (<=1).
        candle = make_candle(6, 15, 5, 7)
        self.assertEqual(shooting_star(candle), Decimal("1"))

    def test_rejects_non_shooting_star_shape(self) -> None:
        candle = make_candle(5, 15, 5, 15)
        self.assertEqual(shooting_star(candle), Decimal("0"))


class EngulfingTests(unittest.TestCase):
    def test_detects_bullish_engulfing(self) -> None:
        previous = make_candle(10, 10.5, 8, 9)   # bearish: close < open
        current = make_candle(8.5, 12, 8, 11)    # bullish and engulfs previous body
        self.assertEqual(bullish_engulfing(previous, current), Decimal("1"))
        self.assertEqual(bearish_engulfing(previous, current), Decimal("0"))

    def test_detects_bearish_engulfing(self) -> None:
        previous = make_candle(9, 10.5, 8.5, 10)  # bullish: close > open
        current = make_candle(10.5, 11, 8, 8.5)   # bearish and engulfs previous body
        self.assertEqual(bearish_engulfing(previous, current), Decimal("1"))
        self.assertEqual(bullish_engulfing(previous, current), Decimal("0"))

    def test_no_engulfing_when_bodies_dont_contain(self) -> None:
        previous = make_candle(10, 10.5, 9.5, 9.8)
        current = make_candle(9.9, 10.2, 9.7, 10.0)
        self.assertEqual(bullish_engulfing(previous, current), Decimal("0"))
        self.assertEqual(bearish_engulfing(previous, current), Decimal("0"))


class DetectPatternsTests(unittest.TestCase):
    def test_empty_candles_returns_all_none(self) -> None:
        result = detect_patterns([])
        self.assertIsNone(result["doji"])
        self.assertIsNone(result["bullish_engulfing"])

    def test_single_candle_leaves_engulfing_none(self) -> None:
        result = detect_patterns([make_candle(10, 11, 9, 10.1)])
        self.assertIsNotNone(result["doji"])
        self.assertIsNone(result["bullish_engulfing"])
        self.assertIsNone(result["bearish_engulfing"])

    def test_two_candles_fills_all_fields(self) -> None:
        candles = [
            make_candle(10, 10.5, 8, 9),
            make_candle(8.5, 12, 8, 11),
        ]
        result = detect_patterns(candles)
        self.assertEqual(result["bullish_engulfing"], Decimal("1"))


if __name__ == "__main__":
    unittest.main()
