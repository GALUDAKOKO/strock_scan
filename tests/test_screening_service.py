from datetime import datetime, timedelta
from decimal import Decimal
import unittest

from girp.domain import Asset, Candle, ProviderInfo
from girp.screening import ScreeningService
from girp.services import MarketDataService
from girp.storage import SQLiteCache


class FakeProvider:
    def refresh(self, symbol: str) -> None:
        return None

    def get_history(self, symbol, start=None, end=None, interval="1d"):
        base = Decimal("10") if symbol.upper() == "PASS" else Decimal("30")
        step = Decimal("1") if symbol.upper() == "PASS" else Decimal("-1")
        return [
            Candle(
                symbol=symbol.upper(),
                timestamp=datetime(2024, 1, 1) + timedelta(days=index),
                open=base + (step * index),
                high=base + (step * index) + Decimal("1"),
                low=base + (step * index) - Decimal("1"),
                close=base + (step * index),
                volume=1000 + index,
            )
            for index in range(25)
        ]

    def get_financials(self, symbol):
        return []

    def get_info(self, symbol):
        sector = "Technology" if symbol.upper() == "PASS" else "Energy"
        return Asset(symbol=symbol.upper(), sector=sector, industry="Software", country="USA", exchange="NASDAQ")

    def provider_info(self):
        return ProviderInfo("fake", True, True, True)


class ScreeningServiceTests(unittest.TestCase):
    def test_screens_symbols_with_formula(self) -> None:
        market_data = MarketDataService(FakeProvider(), SQLiteCache(":memory:"))
        service = ScreeningService(market_data)

        results = service.screen(["PASS", "FAIL"], "close > sma_20 AND rsi_14 > 50")

        self.assertTrue(results[0].passed)
        self.assertFalse(results[1].passed)
        self.assertIn("sma_20", results[0].metrics)

    def test_classification_fields_available_in_metrics(self) -> None:
        market_data = MarketDataService(FakeProvider(), SQLiteCache(":memory:"))
        service = ScreeningService(market_data)

        results = service.screen(["PASS"], "close > 0")

        self.assertEqual(results[0].metrics["sector"], "Technology")
        self.assertEqual(results[0].metrics["industry"], "Software")
        self.assertEqual(results[0].metrics["country"], "USA")
        self.assertEqual(results[0].metrics["exchange"], "NASDAQ")

    def test_can_filter_screen_by_sector(self) -> None:
        market_data = MarketDataService(FakeProvider(), SQLiteCache(":memory:"))
        service = ScreeningService(market_data)

        results = service.screen(["PASS", "FAIL"], 'sector = "Technology"')

        passed_symbols = [result.symbol for result in results if result.passed]
        self.assertEqual(passed_symbols, ["PASS"])


if __name__ == "__main__":
    unittest.main()