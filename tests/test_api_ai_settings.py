import unittest

from fastapi import HTTPException

import girp.api.main as api_main
from girp.ai import LazyProvider
from girp.storage import SQLiteCache


class ApiAiSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_cache_factory = api_main._ai_settings_cache
        self._cache = SQLiteCache(":memory:")
        api_main._ai_settings_cache = lambda: self._cache

    def tearDown(self) -> None:
        api_main._ai_settings_cache = self._original_cache_factory

    def test_get_settings_reports_not_configured_when_nothing_saved_and_no_env(self) -> None:
        result = api_main.ai_get_settings()
        self.assertFalse(result["configured"])
        self.assertIsNone(result["source"])

    def test_save_settings_rejects_unknown_provider(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            api_main.ai_save_settings({"provider": "made-up", "api_key": "key-123"})
        self.assertEqual(ctx.exception.status_code, 400)

    def test_save_settings_rejects_missing_api_key(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            api_main.ai_save_settings({"provider": "anthropic", "api_key": ""})
        self.assertEqual(ctx.exception.status_code, 400)

    def test_save_settings_succeeds_even_without_sdk_installed(self) -> None:
        # The anthropic package is not installed in this environment -- saving must
        # still succeed, since the key is only actually used lazily via LazyProvider.
        result = api_main.ai_save_settings({"provider": "anthropic", "api_key": "sk-ant-abc123"})
        self.assertTrue(result["saved"])
        self.assertEqual(result["provider"], "anthropic")
        self.assertTrue(result["api_key_masked"].endswith("3123") or result["api_key_masked"].endswith("123"))

    def test_get_settings_reflects_saved_provider_masked(self) -> None:
        api_main.ai_save_settings({"provider": "openai", "api_key": "sk-openai-abcdef"})
        result = api_main.ai_get_settings()
        self.assertTrue(result["configured"])
        self.assertEqual(result["source"], "saved")
        self.assertEqual(result["provider"], "openai")
        self.assertNotIn("sk-openai-abcdef", result["api_key_masked"])
        self.assertTrue(result["api_key_masked"].endswith("cdef"))

    def test_delete_settings_clears_saved_config(self) -> None:
        api_main.ai_save_settings({"provider": "anthropic", "api_key": "sk-ant-abc123"})
        deleted = api_main.ai_delete_settings()
        self.assertTrue(deleted["deleted"])
        result = api_main.ai_get_settings()
        self.assertFalse(result["configured"])

    def test_get_ai_service_uses_saved_settings_over_env(self) -> None:
        api_main.ai_save_settings({"provider": "anthropic", "api_key": "sk-ant-abc123"})
        service = api_main.get_ai_service()
        self.assertIsInstance(service._provider, LazyProvider)

    def test_explain_formula_still_works_when_saved_provider_sdk_is_missing(self) -> None:
        # Regression guard: saving a provider whose SDK isn't installed must not break
        # the deterministic (no-LLM) endpoints.
        api_main.ai_save_settings({"provider": "anthropic", "api_key": "sk-ant-abc123"})
        result = api_main.ai_explain_formula({"formula": "close > sma_20"})
        self.assertIn("closing price", result["explanation"])

    def test_summarize_returns_502_when_saved_provider_sdk_is_missing(self) -> None:
        api_main.ai_save_settings({"provider": "anthropic", "api_key": "sk-ant-abc123"})
        with self.assertRaises(HTTPException) as ctx:
            api_main.ai_summarize({"symbol": "AAPL", "metrics": {"pe": 20}})
        self.assertEqual(ctx.exception.status_code, 502)


if __name__ == "__main__":
    unittest.main()
