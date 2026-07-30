from datetime import datetime, timedelta
from decimal import Decimal
import unittest

from girp.backtesting import BacktestService
from girp.domain import Asset, Candle, ProviderInfo
from girp.services import MarketDataService
from girp.storage import SQLiteCache


class UptrendProvider:
    """A clean, steady uptrend: close rises by 1 every day for 40 days."""

    def get_history(self, symbol, start=None, end=None, interval="1d"):
        return [
            Candle(
                symbol=symbol.upper(),
                timestamp=datetime(2024, 1, 1) + timedelta(days=index),
                open=Decimal("100") + Decimal(index),
                high=Decimal("101") + Decimal(index),
                low=Decimal("99") + Decimal(index),
                close=Decimal("100") + Decimal(index),
                volume=1000,
            )
            for index in range(40)
        ]

    def get_financials(self, symbol):
        return []

    def get_info(self, symbol):
        return Asset(symbol=symbol.upper())

    def provider_info(self):
        return ProviderInfo("fake", True, True, True)


class ChoppyProvider:
    """Alternates up/down in waves to force multiple round trips against SMA-20, some winning, some losing."""

    def get_history(self, symbol, start=None, end=None, interval="1d"):
        base = [100, 103, 106, 109, 112, 115, 112, 108, 104, 100]
        pattern = base * 6  # 60 bars, long enough for sma_20 to be defined for most of the run
        return [
            Candle(
                symbol=symbol.upper(),
                timestamp=datetime(2024, 1, 1) + timedelta(days=index),
                open=Decimal(price),
                high=Decimal(price) + 1,
                low=Decimal(price) - 1,
                close=Decimal(price),
                volume=1000,
            )
            for index, price in enumerate(pattern)
        ]

    def get_financials(self, symbol):
        return []

    def get_info(self, symbol):
        return Asset(symbol=symbol.upper())

    def provider_info(self):
        return ProviderInfo("fake", True, True, True)


class CommissionSlippageTests(unittest.TestCase):
    def test_zero_defaults_match_prior_behavior(self) -> None:
        service = BacktestService(MarketDataService(UptrendProvider(), SQLiteCache(":memory:")))
        result = service.run("ABC", "close > sma_20", initial_cash=Decimal("1000"))
        self.assertEqual(result.commission_pct, Decimal("0"))
        self.assertEqual(result.slippage_pct, Decimal("0"))
        # No slippage: the first buy executes exactly at that bar's close.
        first_buy = result.trades[0]
        matching_point = next(p for p in result.equity_curve if p["timestamp"] == first_buy.timestamp)
        self.assertEqual(first_buy.price, matching_point["close"])

    def test_commission_reduces_final_equity(self) -> None:
        no_fee = BacktestService(MarketDataService(UptrendProvider(), SQLiteCache(":memory:"))).run(
            "ABC", "close > sma_20", initial_cash=Decimal("1000")
        )
        with_fee = BacktestService(MarketDataService(UptrendProvider(), SQLiteCache(":memory:"))).run(
            "ABC", "close > sma_20", initial_cash=Decimal("1000"), commission_pct=Decimal("0.01")
        )
        self.assertLess(with_fee.final_equity, no_fee.final_equity)

    def test_slippage_makes_buy_price_worse(self) -> None:
        result = BacktestService(MarketDataService(UptrendProvider(), SQLiteCache(":memory:"))).run(
            "ABC", "close > sma_20", initial_cash=Decimal("1000"), slippage_pct=Decimal("0.05")
        )
        first_buy = result.trades[0]
        # The buy bar's close is available in the matching equity_curve entry.
        matching_point = next(p for p in result.equity_curve if p["timestamp"] == first_buy.timestamp)
        self.assertGreater(first_buy.price, matching_point["close"])
        self.assertEqual(first_buy.price, matching_point["close"] * Decimal("1.05"))

    def test_rejects_negative_commission_or_slippage(self) -> None:
        service = BacktestService(MarketDataService(UptrendProvider(), SQLiteCache(":memory:")))
        with self.assertRaises(ValueError):
            service.run("ABC", "close > 0", commission_pct=Decimal("-0.01"))
        with self.assertRaises(ValueError):
            service.run("ABC", "close > 0", slippage_pct=Decimal("-0.01"))


class CagrTests(unittest.TestCase):
    def test_none_when_history_too_short_for_a_year(self) -> None:
        # 40 days is far short of a year, but CAGR should still compute a (large, annualized) number,
        # not None -- None is reserved for zero/negative equity or non-positive elapsed time.
        service = BacktestService(MarketDataService(UptrendProvider(), SQLiteCache(":memory:")))
        result = service.run("ABC", "close > sma_20", initial_cash=Decimal("1000"))
        self.assertIsNotNone(result.cagr_pct)

    def test_positive_return_yields_positive_cagr(self) -> None:
        service = BacktestService(MarketDataService(UptrendProvider(), SQLiteCache(":memory:")))
        result = service.run("ABC", "close > sma_20", initial_cash=Decimal("1000"))
        self.assertGreater(result.cagr_pct, Decimal("0"))


class SharpeRatioTests(unittest.TestCase):
    def test_none_for_flat_equity_curve(self) -> None:
        result = BacktestService(MarketDataService(UptrendProvider(), SQLiteCache(":memory:"))).run(
            "ABC", "close < 0", initial_cash=Decimal("1000")  # never triggers -> equity stays flat cash
        )
        self.assertIsNone(result.sharpe_ratio)

    def test_positive_for_steady_uptrend(self) -> None:
        result = BacktestService(MarketDataService(UptrendProvider(), SQLiteCache(":memory:"))).run(
            "ABC", "close > sma_20", initial_cash=Decimal("1000")
        )
        self.assertIsNotNone(result.sharpe_ratio)
        self.assertGreater(result.sharpe_ratio, Decimal("0"))


class RoundTripStatsTests(unittest.TestCase):
    def test_win_rate_and_profit_factor_on_choppy_series(self) -> None:
        service = BacktestService(MarketDataService(ChoppyProvider(), SQLiteCache(":memory:")))
        result = service.run("ABC", "close > sma_20", initial_cash=Decimal("1000"))

        # There must be at least one completed round trip to compute win rate at all.
        self.assertIsNotNone(result.win_rate_pct)
        self.assertGreaterEqual(result.win_count + result.loss_count, 1)
        self.assertEqual(
            result.win_rate_pct,
            (Decimal(result.win_count) / Decimal(result.win_count + result.loss_count)) * Decimal("100"),
        )

    def test_none_when_no_round_trips_complete(self) -> None:
        # Formula never triggers a buy -> no trades -> no round trips.
        service = BacktestService(MarketDataService(UptrendProvider(), SQLiteCache(":memory:")))
        result = service.run("ABC", "close < 0", initial_cash=Decimal("1000"))
        self.assertIsNone(result.win_rate_pct)
        self.assertIsNone(result.profit_factor)
        self.assertEqual(result.win_count, 0)
        self.assertEqual(result.loss_count, 0)


if __name__ == "__main__":
    unittest.main()
