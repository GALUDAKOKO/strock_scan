import unittest
from unittest.mock import patch

from girp.ai.provider import AnthropicProvider, LazyProvider, build_provider


class BuildProviderTests(unittest.TestCase):
    def test_builds_anthropic_provider(self) -> None:
        with patch.object(AnthropicProvider, "__init__", return_value=None) as init:
            provider = build_provider("anthropic", "key-123")
        self.assertIsInstance(provider, AnthropicProvider)
        init.assert_called_once_with("key-123")

    def test_passes_model_when_given(self) -> None:
        with patch.object(AnthropicProvider, "__init__", return_value=None) as init:
            build_provider("anthropic", "key-123", model="claude-opus-5")
        init.assert_called_once_with("key-123", model="claude-opus-5")

    def test_raises_value_error_for_unknown_provider(self) -> None:
        with self.assertRaises(ValueError):
            build_provider("not-a-real-provider", "key-123")


class LazyProviderTests(unittest.TestCase):
    def test_does_not_construct_real_provider_until_complete_is_called(self) -> None:
        with patch.object(AnthropicProvider, "__init__", return_value=None):
            lazy = LazyProvider("anthropic", "key-123")
            # Constructing LazyProvider itself must not touch AnthropicProvider at all.
            self.assertIsNone(lazy._built)

    def test_complete_builds_and_delegates_to_real_provider(self) -> None:
        with patch.object(AnthropicProvider, "__init__", return_value=None):
            with patch.object(AnthropicProvider, "complete", return_value="hello") as complete:
                lazy = LazyProvider("anthropic", "key-123")
                result = lazy.complete("prompt text", system="sys")
        self.assertEqual(result, "hello")
        complete.assert_called_once_with("prompt text", system="sys")

    def test_builds_only_once_across_multiple_complete_calls(self) -> None:
        with patch.object(AnthropicProvider, "__init__", return_value=None) as init:
            with patch.object(AnthropicProvider, "complete", return_value="hi"):
                lazy = LazyProvider("anthropic", "key-123")
                lazy.complete("first")
                lazy.complete("second")
        init.assert_called_once()

    def test_raises_runtime_error_when_underlying_sdk_is_missing(self) -> None:
        # No mocking here -- the real anthropic package is not installed in this
        # environment, so this should surface the same clear RuntimeError as
        # AnthropicProvider.__init__ itself would.
        lazy = LazyProvider("anthropic", "key-123")
        with self.assertRaises(RuntimeError):
            lazy.complete("prompt")


if __name__ == "__main__":
    unittest.main()
