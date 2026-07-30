from datetime import datetime, timedelta
from decimal import Decimal
import unittest

from girp.domain import Candle
from girp.technical import ema, percent_distance, rsi, sma, summarize_history


class IndicatorTests(unittest.TestCase):
    def test_sma_ema_and_rsi(self) -> None:
        values = [Decimal(i) for i in range(1, 31)]

        self.assertEqual(sma(values, 20), Decimal("20.5"))
        self.assertIsNotNone(ema(values, 20))
        self.assertEqual(rsi(values, 14), Decimal("100"))

    def test_summarizes_latest_history(self) -> None:
        candles = [
            Candle(
                symbol="ABC",
                timestamp=datetime(2024, 1, 1) + timedelta(days=index),
                open=Decimal(index + 1),
                high=Decimal(index + 2),
                low=Decimal(index),
                close=Decimal(index + 1),
                volume=100 + index,
            )
            for index in range(25)
        ]

        metrics = summarize_history(candles)

        self.assertEqual(metrics["symbol"], "ABC")
        self.assertEqual(metrics["close"], Decimal("25"))
        self.assertEqual(metrics["volume"], 124)
        self.assertEqual(metrics["sma_20"], Decimal("15.5"))
        self.assertEqual(metrics["close_vs_sma_20"], percent_distance(Decimal("25"), Decimal("15.5")))
        self.assertIsNotNone(metrics["momentum_score"])


if __name__ == "__main__":
    unittest.main()