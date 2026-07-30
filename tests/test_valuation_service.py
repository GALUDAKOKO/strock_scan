from datetime import date, datetime
from decimal import Decimal
import unittest

from girp.domain import Asset, Candle, FinancialStatement, ProviderInfo
from girp.services import MarketDataService
from girp.storage import SQLiteCache
from girp.valuation import ValuationService, dcf_fair_value, graham_number, margin_of_safety


class GrahamTests(unittest.TestCase):
    def test_computes_graham_number(self) -> None:
        result = graham_number(Decimal("1.8"), Decimal("2"))
        self.assertEqual(result, Decimal("9"))

    def test_none_for_negative_eps(self) -> None:
        self.assertIsNone(graham_number(Decimal("-1"), Decimal("10")))

    def test_margin_of_safety_positive_when_undervalued(self) -> None:
        mos = margin_of_safety(Decimal("20"), Decimal("15"))
        self.assertEqual(mos, Decimal("25"))


class DCFTests(unittest.TestCase):
    def test_none_without_free_cash_flow(self) -> None:
        self.assertIsNone(dcf_fair_value(None, Decimal("1000")))

    def test_returns_positive_fair_value(self) -> None:
        value = dcf_fair_value(
            Decimal("100000"),
            Decimal("10000"),
            growth_rate=Decimal("0.05"),
            discount_rate=Decimal("0.10"),
            terminal_growth=Decimal("0.02"),
            years=5,
        )
        self.assertIsNotNone(value)
        self.assertGreater(value, Decimal("0"))


class FakeProvider:
    def refresh(self, symbol: str) -> None:
        return None

    def get_history(self, symbol, start=None, end=None, interval="1d"):
        return [
            Candle(
                symbol=symbol.upper(),
                timestamp=datetime(2025, 12, 31),
                open=Decimal("28"),
                high=Decimal("31"),
                low=Decimal("27"),
                close=Decimal("30"),
                volume=1000,
            )
        ]

    def get_financials(self, symbol):
        return [
            FinancialStatement(
                symbol=symbol.upper(),
                period="annual",
                reported_at=date(2025, 12, 31),
                metrics={
                    "Total Revenue": 1_200_000,
                    "Net Income": 150_000,
                    "Total Assets": 1_000_000,
                    "Total Stockholder Equity": 600_000,
                    "Diluted Average Shares": 100_000,
                    "Operating Cash Flow": 180_000,
                    "Capital Expenditure": -40_000,
                },
            )
        ]

    def get_info(self, symbol):
        return Asset(symbol=symbol.upper())

    def provider_info(self):
        return ProviderInfo("fake", True, True, True)


class ValuationServiceTests(unittest.TestCase):
    def test_valuates_symbol_end_to_end(self) -> None:
        market_data = MarketDataService(FakeProvider(), SQLiteCache(":memory:"))
        service = ValuationService(market_data)

        result = service.valuate("ABC")

        self.assertEqual(result.symbol, "ABC")
        self.assertIsNone(result.error)
        self.assertEqual(result.price, Decimal("30"))
        self.assertEqual(result.eps, Decimal("1.5"))
        self.assertIsNotNone(result.graham_number)
        self.assertIsNotNone(result.dcf_fair_value)


if __name__ == "__main__":
    unittest.main()
