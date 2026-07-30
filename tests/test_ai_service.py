import unittest

from girp.ai.provider import AIProviderNotConfigured, UnconfiguredProvider
from girp.ai.service import AIService


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def complete(self, prompt: str, system: str | None = None) -> str:
        self.calls.append((prompt, system))
        return "FAKE_RESPONSE"


class AIServiceDeterministicFeaturesTests(unittest.TestCase):
    """explain_formula/debug_formula must work even with the default (unconfigured) provider."""

    def test_explain_formula_works_without_any_provider_configured(self) -> None:
        service = AIService(provider=UnconfiguredProvider())
        result = service.explain_formula("close > sma_20")
        self.assertIn("closing price", result)

    def test_debug_formula_works_without_any_provider_configured(self) -> None:
        service = AIService(provider=UnconfiguredProvider())
        result = service.debug_formula("close > sma_20")
        self.assertTrue(result.is_valid)


class AIServiceLLMFeaturesTests(unittest.TestCase):
    def test_summarize_raises_when_unconfigured(self) -> None:
        service = AIService(provider=UnconfiguredProvider())
        with self.assertRaises(AIProviderNotConfigured):
            service.summarize("AAPL", {"pe": 20})

    def test_summarize_calls_injected_provider_and_returns_its_output(self) -> None:
        fake = FakeProvider()
        service = AIService(provider=fake)
        result = service.summarize("AAPL", {"pe": 20, "roe": 15})
        self.assertEqual(result, "FAKE_RESPONSE")
        self.assertEqual(len(fake.calls), 1)
        prompt, system = fake.calls[0]
        self.assertIn("AAPL", prompt)
        self.assertIn("pe", prompt)
        self.assertIsNotNone(system)

    def test_compare_calls_injected_provider_with_all_symbols(self) -> None:
        fake = FakeProvider()
        service = AIService(provider=fake)
        result = service.compare(["AAPL", "MSFT"], {"AAPL": {"pe": 20}, "MSFT": {"pe": 30}})
        self.assertEqual(result, "FAKE_RESPONSE")
        prompt, _ = fake.calls[0]
        self.assertIn("AAPL", prompt)
        self.assertIn("MSFT", prompt)

    def test_suggest_strategy_calls_injected_provider(self) -> None:
        fake = FakeProvider()
        service = AIService(provider=fake)
        result = service.suggest_strategy("high quality low volatility stocks")
        self.assertEqual(result, "FAKE_RESPONSE")
        prompt, _ = fake.calls[0]
        self.assertIn("high quality low volatility stocks", prompt)

    def test_optimize_strategy_calls_injected_provider(self) -> None:
        fake = FakeProvider()
        service = AIService(provider=fake)
        result = service.optimize_strategy("close > sma_20", {"sharpe_ratio": 0.5})
        self.assertEqual(result, "FAKE_RESPONSE")
        prompt, _ = fake.calls[0]
        self.assertIn("close > sma_20", prompt)
        self.assertIn("sharpe_ratio", prompt)

    def test_thai_language_uses_thai_system_prompt(self) -> None:
        fake = FakeProvider()
        service = AIService(provider=fake)
        service.summarize("AAPL", {"pe": 20}, lang="th")
        _, system = fake.calls[0]
        self.assertIn("GUMPOL", system)


if __name__ == "__main__":
    unittest.main()
