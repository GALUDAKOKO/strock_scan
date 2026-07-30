from datetime import datetime, timedelta
from decimal import Decimal
import unittest

from fastapi import HTTPException

import girp.api.main as api_main
from girp.domain import Asset, Candle, ProviderInfo
from girp.services import MarketDataService
from girp.storage import SQLiteCache


class FakeProvider:
    def get_history(self, symbol, start=None, end=None, interval="1d"):
        return [
            Candle(
                symbol=symbol.upper(),
                timestamp=datetime(2024, 1, 1) + timedelta(days=index),
                open=Decimal(10) + Decimal(index) * Decimal("0.1"),
                high=Decimal(11) + Decimal(index) * Decimal("0.1"),
                low=Decimal(9) + Decimal(index) * Decimal("0.1"),
                close=Decimal(10) + Decimal(index) * Decimal("0.1"),
                volume=1000 + index,
            )
            for index in range(60)
        ]

    def get_financials(self, symbol):
        return []

    def get_info(self, symbol):
        return Asset(symbol=symbol.upper(), market="NYSE", name="Example Inc")

    def provider_info(self):
        return ProviderInfo("fake", True, True, True)


class ApiTechnicalsEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_get_service = api_main.get_service
        cache = SQLiteCache(":memory:")
        api_main.get_service = lambda: MarketDataService(FakeProvider(), cache)

    def tearDown(self) -> None:
        api_main.get_service = self._original_get_service

    def test_returns_full_indicator_set(self) -> None:
        result = api_main.technicals("abc")

        self.assertEqual(result["symbol"], "ABC")
        self.assertIn("macd", result["metrics"])
        self.assertIn("atr_14", result["metrics"])
        self.assertIn("adx_14", result["metrics"])
        self.assertIn("pattern_doji", result["metrics"])
        self.assertIn("supertrend_direction", result["metrics"])
        self.assertIsNotNone(result["updated_at"])
        # symbol/timestamp are surfaced as top-level fields, not duplicated inside metrics.
        self.assertNotIn("symbol", result["metrics"])
        self.assertNotIn("timestamp", result["metrics"])

    def test_raises_404_when_no_history(self) -> None:
        class EmptyProvider(FakeProvider):
            def get_history(self, symbol, start=None, end=None, interval="1d"):
                return []

        api_main.get_service = lambda: MarketDataService(EmptyProvider(), SQLiteCache(":memory:"))
        with self.assertRaises(HTTPException) as ctx:
            api_main.technicals("abc")
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
