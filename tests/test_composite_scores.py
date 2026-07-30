from decimal import Decimal
import unittest

from girp.ranking.composite import compute_composite_scores


class CompositeScoresTests(unittest.TestCase):
    def test_higher_roe_scores_higher_quality(self) -> None:
        metrics = {
            "AAA": {"roe": Decimal("0.30")},
            "BBB": {"roe": Decimal("0.10")},
            "CCC": {"roe": Decimal("0.05")},
        }
        scores = compute_composite_scores(metrics)
        self.assertGreater(scores["AAA"]["score_quality"], scores["BBB"]["score_quality"])
        self.assertGreater(scores["BBB"]["score_quality"], scores["CCC"]["score_quality"])

    def test_lower_pe_scores_higher_value(self) -> None:
        metrics = {
            "CHEAP": {"pe": Decimal("8")},
            "FAIR": {"pe": Decimal("15")},
            "EXPENSIVE": {"pe": Decimal("40")},
        }
        scores = compute_composite_scores(metrics)
        self.assertGreater(scores["CHEAP"]["score_value"], scores["FAIR"]["score_value"])
        self.assertGreater(scores["FAIR"]["score_value"], scores["EXPENSIVE"]["score_value"])

    def test_lower_debt_and_lower_atr_scores_higher_risk(self) -> None:
        # Risk score is inverted: low debt-to-equity and low ATR% should score *higher* (safer).
        metrics = {
            "SAFE": {"debt_to_equity": Decimal("0.2"), "atr_14": Decimal("1"), "close": Decimal("100")},
            "RISKY": {"debt_to_equity": Decimal("3.0"), "atr_14": Decimal("10"), "close": Decimal("100")},
        }
        scores = compute_composite_scores(metrics)
        self.assertGreater(scores["SAFE"]["score_risk"], scores["RISKY"]["score_risk"])

    def test_missing_category_factors_yields_none(self) -> None:
        # No fundamentals at all -> quality/growth/value must be None, not a default 0/50.
        metrics = {
            "AAA": {"close": Decimal("100"), "momentum_score": Decimal("5")},
            "BBB": {"close": Decimal("100"), "momentum_score": Decimal("2")},
        }
        scores = compute_composite_scores(metrics)
        self.assertIsNone(scores["AAA"]["score_quality"])
        self.assertIsNone(scores["AAA"]["score_growth"])
        self.assertIsNone(scores["AAA"]["score_value"])
        self.assertIsNotNone(scores["AAA"]["score_momentum"])

    def test_overall_is_average_of_available_categories(self) -> None:
        metrics = {
            "AAA": {"roe": Decimal("0.20"), "momentum_score": Decimal("5")},
            "BBB": {"roe": Decimal("0.05"), "momentum_score": Decimal("1")},
        }
        scores = compute_composite_scores(metrics)
        expected_overall_aaa = (scores["AAA"]["score_quality"] + scores["AAA"]["score_momentum"]) / Decimal(2)
        self.assertEqual(scores["AAA"]["score_overall"], expected_overall_aaa)

    def test_single_symbol_gets_neutral_fifty_percentile(self) -> None:
        metrics = {"ONLY": {"roe": Decimal("0.15")}}
        scores = compute_composite_scores(metrics)
        self.assertEqual(scores["ONLY"]["score_quality"], Decimal("50"))

    def test_empty_input_returns_empty_dict(self) -> None:
        self.assertEqual(compute_composite_scores({}), {})

    def test_tied_values_share_the_same_percentile(self) -> None:
        metrics = {
            "AAA": {"roe": Decimal("0.10")},
            "BBB": {"roe": Decimal("0.10")},
            "CCC": {"roe": Decimal("0.20")},
        }
        scores = compute_composite_scores(metrics)
        self.assertEqual(scores["AAA"]["score_quality"], scores["BBB"]["score_quality"])
        self.assertGreater(scores["CCC"]["score_quality"], scores["AAA"]["score_quality"])


if __name__ == "__main__":
    unittest.main()
