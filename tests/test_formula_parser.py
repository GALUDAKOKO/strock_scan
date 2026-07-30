from decimal import Decimal
import unittest

from girp.formula import ParseError, parse_formula


class FormulaParserTests(unittest.TestCase):
    def test_parses_comparison_chain(self) -> None:
        formula = parse_formula('pe < 15 AND roe >= 10 OR market = "SET"')

        self.assertEqual(formula.first.left, "pe")
        self.assertEqual(formula.first.operator, "<")
        self.assertEqual(formula.first.right, Decimal("15"))
        self.assertEqual(formula.rest[0][0], "AND")
        self.assertEqual(formula.rest[0][1].left, "roe")
        self.assertEqual(formula.rest[1][0], "OR")
        self.assertEqual(formula.rest[1][1].right, "SET")

    def test_rejects_empty_formula(self) -> None:
        with self.assertRaises(ParseError):
            parse_formula("")


if __name__ == "__main__":
    unittest.main()
