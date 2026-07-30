from datetime import datetime, timedelta
from decimal import Decimal
import unittest

from girp.domain import Asset, Candle, ProviderInfo
from girp.ranking import RankingService
from girp.services import MarketDataService
from girp.storage import SQLiteCache


class FakeProvider:
    def refresh(self, symbol: str) -> None:
        return None

    def get_history(self, symbol, start=None, end=None, interval="1d"):
        step = Decimal("2") if symbol.upper() == "FAST" else Decimal("1")
        return [
            Candle(
                symbol=symbol.upper(),
                timestamp=datetime(2024, 1, 1) + timedelta(days=index),
                open=Decimal("10") + (step * index),
                high=Decimal("11") + (step * index),
                low=Decimal("9") + (step * index),
                close=Decimal("10") + (step * index),
                volume=1000 + index,
            )
            for index in range(30)
        ]

    def get_financials(self, symbol):
        return []

    def get_info(self, symbol):
        return Asset(symbol=symbol.upper())

    def provider_info(self):
        return ProviderInfo("fake", True, True, True)


class RankingServiceTests(unittest.TestCase):
    def test_ranks_symbols_by_metric(self) -> None:
        market_data = MarketDataService(FakeProvider(), SQLiteCache(":memory:"))
        service = RankingService(market_data)

        results = service.rank(["SLOW", "FAST"], sort_by="close", descending=True)

        self.assertEqual(results[0].rank, 1)
        self.assertEqual(results[0].symbol, "FAST")
        self.assertEqual(results[1].rank, 2)
        self.assertEqual(results[1].symbol, "SLOW")

    def test_applies_optional_formula_filter(self) -> None:
        market_data = MarketDataService(FakeProvider(), SQLiteCache(":memory:"))
        service = RankingService(market_data)

        results = service.rank(["SLOW", "FAST"], sort_by="close", formula="close > 50")

        ranked = [result for result in results if result.rank is not None]
        filtered = [result for result in results if not result.passed_filter]
        self.assertEqual([result.symbol for result in ranked], ["FAST"])
        self.assertEqual([result.symbol for result in filtered], ["SLOW"])

    def test_composite_scores_are_merged_into_metrics(self) -> None:
        market_data = MarketDataService(FakeProvider(), SQLiteCache(":memory:"))
        service = RankingService(market_data)

        results = service.rank(["SLOW", "FAST"], sort_by="close")

        for result in results:
            self.assertIn("score_momentum", result.metrics)
            self.assertIn("score_overall", result.metrics)

        # FAST has a steeper close series -> higher momentum_score -> should out-score SLOW
        # on the momentum composite too.
        fast = next(r for r in results if r.symbol == "FAST")
        slow = next(r for r in results if r.symbol == "SLOW")
        self.assertGreater(fast.metrics["score_momentum"], slow.metrics["score_momentum"])

    def test_can_sort_by_composite_overall_score(self) -> None:
        market_data = MarketDataService(FakeProvider(), SQLiteCache(":memory:"))
        service = RankingService(market_data)

        results = service.rank(["SLOW", "FAST"], sort_by="score_overall", descending=True)

        ranked = [result for result in results if result.rank is not None]
        self.assertEqual(ranked[0].symbol, "FAST")


if __name__ == "__main__":
    unittest.main()