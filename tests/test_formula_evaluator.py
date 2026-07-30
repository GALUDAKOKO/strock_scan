from decimal import Decimal
import unittest

from girp.formula import evaluate_formula


class FormulaEvaluatorTests(unittest.TestCase):
    def test_evaluates_metric_to_number_and_metric_to_metric(self) -> None:
        metrics = {
            "close": Decimal("120"),
            "sma_20": Decimal("100"),
            "rsi_14": Decimal("55"),
            "market": "SET",
        }

        self.assertTrue(evaluate_formula("close > sma_20 AND rsi_14 < 70", metrics))
        self.assertTrue(evaluate_formula('market = "SET" AND close >= 120', metrics))
        self.assertFalse(evaluate_formula("close < sma_20", metrics))


if __name__ == "__main__":
    unittest.main()