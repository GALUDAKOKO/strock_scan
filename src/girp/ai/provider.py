from __future__ import annotations

import os
from typing import Protocol


class AIProviderNotConfigured(RuntimeError):
    """Raised when an AI feature needs an LLM but no provider is configured."""


class AIProvider(Protocol):
    def complete(self, prompt: str, system: str | None = None) -> str: ...


class UnconfiguredProvider:
    """Default provider when no API key is set. Fails clearly instead of silently."""

    def complete(self, prompt: str, system: str | None = None) -> str:
        raise AIProviderNotConfigured(
            "No AI provider is configured. Set one of ANTHROPIC_API_KEY, OPENAI_API_KEY, "
            "or GEMINI_API_KEY as an environment variable to enable AI features."
        )


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-5") -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "The 'anthropic' package is not installed. Install it (pip install anthropic) "
                "to use ANTHROPIC_API_KEY."
            ) from exc
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, prompt: str, system: str | None = None) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if hasattr(block, "text"))


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        try:
            import openai
        except ImportError as exc:
            raise RuntimeError(
                "The 'openai' package is not installed. Install it (pip install openai) "
                "to use OPENAI_API_KEY."
            ) from exc
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def complete(self, prompt: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self._client.chat.completions.create(model=self._model, messages=messages)
        return response.choices[0].message.content or ""


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError(
                "The 'google-generativeai' package is not installed. Install it "
                "(pip install google-generativeai) to use GEMINI_API_KEY."
            ) from exc
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    def complete(self, prompt: str, system: str | None = None) -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = self._model.generate_content(full_prompt)
        return response.text or ""


PROVIDER_CLASSES: dict[str, type] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}


def build_provider(provider_name: str, api_key: str, model: str | None = None) -> AIProvider:
    """Construct a provider by name (used for settings saved via the UI, not env vars)."""
    provider_cls = PROVIDER_CLASSES.get(provider_name)
    if provider_cls is None:
        raise ValueError(
            f"Unknown AI provider '{provider_name}'. Supported providers: "
            f"{', '.join(sorted(PROVIDER_CLASSES))}."
        )
    if model:
        return provider_cls(api_key, model=model)
    return provider_cls(api_key)


class LazyProvider:
    """Defers constructing the real provider (and importing its SDK) until first use.

    Used for provider/key combinations saved via the /ai/settings UI: the SDK package for
    that provider may not be installed yet (the user just wants to store a key now), so we
    must not raise at construction time -- only explain_formula/debug_formula are guaranteed
    to work without any provider at all, but they also must not be broken by an unrelated
    "package not installed" error simply because *some* provider happens to be saved.
    """

    def __init__(self, provider_name: str, api_key: str, model: str | None = None) -> None:
        self._provider_name = provider_name
        self._api_key = api_key
        self._model = model
        self._built: AIProvider | None = None

    def complete(self, prompt: str, system: str | None = None) -> str:
        if self._built is None:
            self._built = build_provider(self._provider_name, self._api_key, self._model)
        return self._built.complete(prompt, system=system)


def get_provider() -> AIProvider:
    """Pick a provider from environment variables, in this priority order.

    Anthropic first (this app's own docs/prompting are Claude-oriented), then OpenAI, then
    Gemini, falling back to UnconfiguredProvider (which fails with a clear message rather
    than silently doing nothing) if none are set.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicProvider(os.environ["ANTHROPIC_API_KEY"])
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIProvider(os.environ["OPENAI_API_KEY"])
    if os.environ.get("GEMINI_API_KEY"):
        return GeminiProvider(os.environ["GEMINI_API_KEY"])
    return UnconfiguredProvider()
