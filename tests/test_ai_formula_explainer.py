import unittest

from girp.ai.formula_explainer import debug_formula, explain_formula
from girp.formula import ParseError


class ExplainFormulaTests(unittest.TestCase):
    def test_explains_single_condition_in_english(self) -> None:
        result = explain_formula("close > sma_20")
        self.assertIn("closing price", result)
        self.assertIn("greater than", result)
        self.assertIn("simple moving average", result)

    def test_explains_multi_condition_chain_with_joiners(self) -> None:
        result = explain_formula("close > sma_20 AND rsi_14 < 30")
        self.assertIn("and", result)
        self.assertIn("Relative Strength Index", result)

    def test_explains_in_thai(self) -> None:
        result = explain_formula("pe < 15", lang="th")
        self.assertIn("อัตราส่วนราคาต่อกำไร", result)

    def test_handles_quoted_text_value(self) -> None:
        result = explain_formula('sector = "Technology"')
        self.assertIn("Technology", result)

    def test_raises_parse_error_for_invalid_formula(self) -> None:
        with self.assertRaises(ParseError):
            explain_formula("close >")


class DebugFormulaTests(unittest.TestCase):
    def test_valid_formula_is_reported_valid(self) -> None:
        result = debug_formula("close > sma_20")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.message, "Formula is valid.")
        self.assertTrue(result.suggestions)

    def test_unparseable_formula_reports_error_and_suggestion(self) -> None:
        result = debug_formula("close >")
        self.assertFalse(result.is_valid)
        self.assertIn("Could not parse", result.message)
        self.assertTrue(result.suggestions)

    def test_parenthesis_use_is_flagged_with_specific_suggestion(self) -> None:
        result = debug_formula("(close > sma_20)")
        self.assertFalse(result.is_valid)
        joined = " ".join(result.suggestions)
        self.assertIn("parentheses", joined)

    def test_typo_in_field_name_suggests_closest_match(self) -> None:
        result = debug_formula("close > sma_2O")
        self.assertFalse(result.is_valid)
        joined = " ".join(result.suggestions)
        self.assertIn("sma_20", joined)

    def test_unquoted_text_value_is_flagged(self) -> None:
        result = debug_formula("sector = Technology")
        self.assertFalse(result.is_valid)
        joined = " ".join(result.suggestions)
        self.assertIn("quotes", joined.lower())

    def test_unknown_left_field_is_flagged(self) -> None:
        result = debug_formula("totally_unknown_field > 5")
        self.assertFalse(result.is_valid)
        joined = " ".join(result.suggestions)
        self.assertIn("totally_unknown_field", joined)


if __name__ == "__main__":
    unittest.main()
