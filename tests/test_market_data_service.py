from datetime import datetime
from decimal import Decimal
import unittest

from girp.domain import Asset, Candle, ProviderInfo
from girp.services import MarketDataService
from girp.storage import SQLiteCache


class FakeProvider:
    def __init__(self) -> None:
        self.history_calls = 0
        self.info_calls = 0

    def refresh(self, symbol: str) -> None:
        return None

    def get_history(self, symbol, start=None, end=None, interval="1d"):
        self.history_calls += 1
        return [
            Candle(
                symbol=symbol.upper(),
                timestamp=datetime(2024, 1, 1),
                open=Decimal("1"),
                high=Decimal("2"),
                low=Decimal("0.5"),
                close=Decimal("1.5"),
                volume=100,
            )
        ]

    def get_financials(self, symbol):
        return []

    def get_info(self, symbol):
        self.info_calls += 1
        return Asset(symbol=symbol.upper(), market="NYSE", name="Example Inc")

    def provider_info(self):
        return ProviderInfo("fake", True, True, True)


class MarketDataServiceTests(unittest.TestCase):
    def test_uses_cache_after_first_fetch(self) -> None:
        provider = FakeProvider()
        service = MarketDataService(provider, SQLiteCache(":memory:"))

        first = service.get_history("abc")
        second = service.get_history("abc")

        self.assertEqual(first, second)
        self.assertEqual(provider.history_calls, 1)

    def test_caches_asset_info(self) -> None:
        provider = FakeProvider()
        service = MarketDataService(provider, SQLiteCache(":memory:"))

        service.get_info("abc")
        service.get_info("abc")

        self.assertEqual(provider.info_calls, 1)

    def test_tracks_last_updated_on_fresh_fetch(self) -> None:
        provider = FakeProvider()
        service = MarketDataService(provider, SQLiteCache(":memory:"))

        self.assertIsNone(service.get_last_updated("abc"))

        service.get_history("abc")
        first_touch = service.get_last_updated("abc")
        self.assertIsNotNone(first_touch)

        # Cache hit should not need to touch again, but the value should stay set.
        service.get_history("abc")
        self.assertEqual(service.get_last_updated("abc"), first_touch)

        many = service.get_last_updated_many(["abc", "xyz"])
        self.assertEqual(many["ABC"], first_touch)
        self.assertIsNone(many["XYZ"])


if __name__ == "__main__":
    unittest.main()
