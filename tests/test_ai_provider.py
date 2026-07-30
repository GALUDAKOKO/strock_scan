import os
import unittest
from unittest.mock import patch

from girp.ai.provider import (
    AIProviderNotConfigured,
    AnthropicProvider,
    GeminiProvider,
    OpenAIProvider,
    UnconfiguredProvider,
    get_provider,
)


class GetProviderPrecedenceTests(unittest.TestCase):
    def test_returns_unconfigured_when_no_keys_set(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
                os.environ.pop(var, None)
            provider = get_provider()
        self.assertIsInstance(provider, UnconfiguredProvider)

    def test_prefers_anthropic_when_all_keys_set(self) -> None:
        env = {"ANTHROPIC_API_KEY": "a", "OPENAI_API_KEY": "b", "GEMINI_API_KEY": "c"}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(AnthropicProvider, "__init__", return_value=None) as init:
                provider = get_provider()
        self.assertIsInstance(provider, AnthropicProvider)
        init.assert_called_once_with("a")

    def test_falls_back_to_openai_when_no_anthropic_key(self) -> None:
        env = {"OPENAI_API_KEY": "b", "GEMINI_API_KEY": "c"}
        with patch.dict(os.environ, env, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with patch.object(OpenAIProvider, "__init__", return_value=None) as init:
                provider = get_provider()
        self.assertIsInstance(provider, OpenAIProvider)
        init.assert_called_once_with("b")

    def test_falls_back_to_gemini_when_only_gemini_key_set(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "c"}, clear=True):
            for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
                os.environ.pop(var, None)
            with patch.object(GeminiProvider, "__init__", return_value=None) as init:
                provider = get_provider()
        self.assertIsInstance(provider, GeminiProvider)
        init.assert_called_once_with("c")


class UnconfiguredProviderTests(unittest.TestCase):
    def test_complete_raises_clear_error_naming_all_env_vars(self) -> None:
        provider = UnconfiguredProvider()
        with self.assertRaises(AIProviderNotConfigured) as ctx:
            provider.complete("hello")
        message = str(ctx.exception)
        for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
            self.assertIn(var, message)


if __name__ == "__main__":
    unittest.main()
