from datetime import date
from decimal import Decimal
import unittest

from girp.domain import FinancialStatement
from girp.fundamental import altman_z_score, beneish_m_score, piotroski_f_score


def _annual(reported_at: date, metrics: dict) -> FinancialStatement:
    return FinancialStatement(symbol="ABC", period="annual", reported_at=reported_at, metrics=metrics)


class PiotroskiTests(unittest.TestCase):
    def test_none_with_single_period(self) -> None:
        statements = [_annual(date(2025, 12, 31), {"Net Income": 100})]
        self.assertIsNone(piotroski_f_score(statements))

    def test_scores_a_healthy_improving_company_highly(self) -> None:
        statements = [
            _annual(
                date(2025, 12, 31),
                {
                    "Net Income": 200_000,
                    "Total Assets": 1_000_000,
                    "Operating Cash Flow": 220_000,
                    "Long Term Debt": 100_000,
                    "Total Current Assets": 500_000,
                    "Total Current Liabilities": 200_000,
                    "Diluted Average Shares": 100_000,
                    "Total Revenue": 1_500_000,
                    "Gross Profit": 600_000,
                },
            ),
            _annual(
                date(2024, 12, 31),
                {
                    "Net Income": 100_000,
                    "Total Assets": 900_000,
                    "Operating Cash Flow": 90_000,
                    "Long Term Debt": 150_000,
                    "Total Current Assets": 400_000,
                    "Total Current Liabilities": 250_000,
                    "Diluted Average Shares": 100_000,
                    "Total Revenue": 1_200_000,
                    "Gross Profit": 420_000,
                },
            ),
        ]

        score = piotroski_f_score(statements)

        self.assertIsNotNone(score)
        self.assertGreaterEqual(score, 7)
        self.assertLessEqual(score, 9)


class AltmanTests(unittest.TestCase):
    def test_none_without_market_cap(self) -> None:
        statements = [
            _annual(
                date(2025, 12, 31),
                {
                    "Total Assets": 1_000_000,
                    "Total Current Assets": 500_000,
                    "Total Current Liabilities": 200_000,
                    "Retained Earnings": 300_000,
                    "EBIT": 150_000,
                    "Total Liab": 400_000,
                    "Total Revenue": 1_200_000,
                },
            )
        ]
        self.assertIsNone(altman_z_score(statements, market_cap=None))

    def test_computes_score_with_market_cap(self) -> None:
        statements = [
            _annual(
                date(2025, 12, 31),
                {
                    "Total Assets": 1_000_000,
                    "Total Current Assets": 500_000,
                    "Total Current Liabilities": 200_000,
                    "Retained Earnings": 300_000,
                    "EBIT": 150_000,
                    "Total Liab": 400_000,
                    "Total Revenue": 1_200_000,
                },
            )
        ]
        score = altman_z_score(statements, market_cap=Decimal("2000000"))
        self.assertIsNotNone(score)
        self.assertGreater(score, Decimal("0"))


class BeneishTests(unittest.TestCase):
    def test_none_when_history_insufficient(self) -> None:
        statements = [_annual(date(2025, 12, 31), {"Total Revenue": 100})]
        self.assertIsNone(beneish_m_score(statements))

    def test_none_when_required_fields_missing(self) -> None:
        statements = [
            _annual(date(2025, 12, 31), {"Total Revenue": 100, "Net Income": 10}),
            _annual(date(2024, 12, 31), {"Total Revenue": 90, "Net Income": 8}),
        ]
        self.assertIsNone(beneish_m_score(statements))


if __name__ == "__main__":
    unittest.main()
