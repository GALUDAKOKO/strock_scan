from datetime import date
from decimal import Decimal
import unittest

from girp.domain import FinancialStatement
from girp.fundamental import compute_fundamentals


def _annual(reported_at: date, metrics: dict) -> FinancialStatement:
    return FinancialStatement(symbol="ABC", period="annual", reported_at=reported_at, metrics=metrics)


class ComputeFundamentalsTests(unittest.TestCase):
    def test_computes_ratios_from_two_annual_periods(self) -> None:
        statements = [
            _annual(
                date(2025, 12, 31),
                {
                    "Total Revenue": 1_200_000,
                    "Net Income": 150_000,
                    "Total Assets": 1_000_000,
                    "Total Stockholder Equity": 600_000,
                    "Total Liab": 400_000,
                    "Diluted Average Shares": 100_000,
                    "Operating Cash Flow": 180_000,
                    "Capital Expenditure": -40_000,
                },
            ),
            _annual(
                date(2024, 12, 31),
                {
                    "Total Revenue": 1_000_000,
                    "Net Income": 100_000,
                    "Total Assets": 900_000,
                    "Total Stockholder Equity": 500_000,
                    "Total Liab": 400_000,
                    "Diluted Average Shares": 100_000,
                },
            ),
        ]

        metrics = compute_fundamentals(statements, price=Decimal("30"))

        self.assertEqual(metrics["revenue"], Decimal("1200000"))
        self.assertEqual(metrics["net_income"], Decimal("150000"))
        self.assertEqual(metrics["eps"], Decimal("1.5"))
        self.assertEqual(metrics["book_value_per_share"], Decimal("6"))
        self.assertEqual(metrics["pe"], Decimal("20"))
        self.assertEqual(metrics["pbv"], Decimal("5"))
        self.assertEqual(metrics["roe"], Decimal("0.25"))
        self.assertEqual(metrics["roa"], Decimal("0.15"))
        self.assertEqual(metrics["revenue_growth"], Decimal("0.2"))
        self.assertEqual(metrics["free_cash_flow"], Decimal("140000"))

    def test_returns_none_metrics_when_statements_missing(self) -> None:
        metrics = compute_fundamentals([], price=Decimal("10"))

        self.assertIsNone(metrics["eps"])
        self.assertIsNone(metrics["pe"])
        self.assertIsNone(metrics["roe"])

    def test_falls_back_to_snapshot_when_statements_sparse(self) -> None:
        metrics = compute_fundamentals(
            [],
            price=Decimal("50"),
            snapshot={
                "trailing_eps": "2.5",
                "book_value": "20",
                "shares_outstanding": "1000000",
                "return_on_equity": "0.18",
            },
        )

        self.assertEqual(metrics["eps"], Decimal("2.5"))
        self.assertEqual(metrics["book_value_per_share"], Decimal("20"))
        self.assertEqual(metrics["pe"], Decimal("20"))
        self.assertEqual(metrics["roe"], Decimal("0.18"))


if __name__ == "__main__":
    unittest.main()
