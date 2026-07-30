import unittest

from fastapi import HTTPException

import girp.api.main as api_main
from girp.ai.provider import AIProviderNotConfigured
from girp.ai.service import AIService


class FakeProvider:
    def complete(self, prompt: str, system: str | None = None) -> str:
        return "FAKE_RESPONSE"


class ApiAiDeterministicEndpointsTests(unittest.TestCase):
    """explain-formula / debug-formula must work with the real default get_ai_service
    (i.e. with no API key configured in this test environment)."""

    def test_explain_formula_endpoint_returns_explanation(self) -> None:
        result = api_main.ai_explain_formula({"formula": "close > sma_20"})
        self.assertEqual(result["formula"], "close > sma_20")
        self.assertIn("closing price", result["explanation"])

    def test_explain_formula_endpoint_rejects_missing_formula(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            api_main.ai_explain_formula({})
        self.assertEqual(ctx.exception.status_code, 400)

    def test_explain_formula_endpoint_returns_400_on_parse_error(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            api_main.ai_explain_formula({"formula": "close >"})
        self.assertEqual(ctx.exception.status_code, 400)

    def test_debug_formula_endpoint_reports_valid_formula(self) -> None:
        result = api_main.ai_debug_formula({"formula": "close > sma_20"})
        self.assertTrue(result["is_valid"])

    def test_debug_formula_endpoint_reports_invalid_formula_without_raising(self) -> None:
        result = api_main.ai_debug_formula({"formula": "close >"})
        self.assertFalse(result["is_valid"])
        self.assertTrue(result["suggestions"])


class ApiAiLLMEndpointsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_get_ai_service = api_main.get_ai_service

    def tearDown(self) -> None:
        api_main.get_ai_service = self._original_get_ai_service

    def test_summarize_returns_503_when_no_provider_configured(self) -> None:
        # Default environment in tests has no API keys set, so this should surface
        # the graceful "not configured" error rather than crashing.
        with self.assertRaises(HTTPException) as ctx:
            api_main.ai_summarize({"symbol": "AAPL", "metrics": {"pe": 20}})
        self.assertEqual(ctx.exception.status_code, 503)

    def test_summarize_succeeds_with_injected_fake_provider(self) -> None:
        api_main.get_ai_service = lambda: AIService(provider=FakeProvider())
        result = api_main.ai_summarize({"symbol": "AAPL", "metrics": {"pe": 20}})
        self.assertEqual(result["summary"], "FAKE_RESPONSE")

    def test_compare_succeeds_with_injected_fake_provider(self) -> None:
        api_main.get_ai_service = lambda: AIService(provider=FakeProvider())
        result = api_main.ai_compare(
            {"symbols": ["AAPL", "MSFT"], "metrics_by_symbol": {"AAPL": {"pe": 20}, "MSFT": {"pe": 30}}}
        )
        self.assertEqual(result["comparison"], "FAKE_RESPONSE")

    def test_suggest_strategy_succeeds_with_injected_fake_provider(self) -> None:
        api_main.get_ai_service = lambda: AIService(provider=FakeProvider())
        result = api_main.ai_suggest_strategy({"goal": "high momentum stocks"})
        self.assertEqual(result["suggestion"], "FAKE_RESPONSE")

    def test_optimize_strategy_succeeds_with_injected_fake_provider(self) -> None:
        api_main.get_ai_service = lambda: AIService(provider=FakeProvider())
        result = api_main.ai_optimize_strategy(
            {"formula": "close > sma_20", "backtest_metrics": {"sharpe_ratio": 0.5}}
        )
        self.assertEqual(result["suggestion"], "FAKE_RESPONSE")

    def test_summarize_rejects_missing_symbol(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            api_main.ai_summarize({"metrics": {}})
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
