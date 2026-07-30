from datetime import datetime, timedelta
from decimal import Decimal
import unittest

from girp.backtesting import BacktestService
from girp.domain import Asset, Candle, ProviderInfo
from girp.services import MarketDataService
from girp.storage import SQLiteCache


class FakeProvider:
    def refresh(self, symbol: str) -> None:
        return None

    def get_history(self, symbol, start=None, end=None, interval="1d"):
        return [
            Candle(
                symbol=symbol.upper(),
                timestamp=datetime(2024, 1, 1) + timedelta(days=index),
                open=Decimal("100") + Decimal(index),
                high=Decimal("101") + Decimal(index),
                low=Decimal("99") + Decimal(index),
                close=Decimal("100") + Decimal(index),
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


class BacktestServiceTests(unittest.TestCase):
    def test_runs_long_only_backtest(self) -> None:
        market_data = MarketDataService(FakeProvider(), SQLiteCache(":memory:"))
        service = BacktestService(market_data)

        result = service.run("ABC", "close > sma_20", initial_cash=Decimal("1000"))

        self.assertEqual(result.symbol, "ABC")
        self.assertGreater(result.final_equity, Decimal("1000"))
        self.assertGreaterEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0].side, "BUY")
        self.assertEqual(len(result.equity_curve), 30)

    def test_returns_empty_result_for_no_history(self) -> None:
        class EmptyProvider(FakeProvider):
            def get_history(self, symbol, start=None, end=None, interval="1d"):
                return []

        market_data = MarketDataService(EmptyProvider(), SQLiteCache(":memory:"))
        service = BacktestService(market_data)

        result = service.run("ABC", "close > 0")

        self.assertEqual(result.final_equity, result.initial_cash)
        self.assertEqual(result.error, "No price history available.")


if __name__ == "__main__":
    unittest.main()