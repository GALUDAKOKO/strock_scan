# GIRP Phase 10 — AI Layer

Phase 10 adds an AI layer to GUMPOL_ระบบคัดกรองหุ้น: a provider-agnostic LLM abstraction plus
four user-facing features (Formula Explain & Debug, AI Summary, AI Compare, Strategy Suggest &
Optimize). The user has no LLM API key yet, so the whole layer is built to degrade gracefully:
Formula Explain & Debug needs no LLM at all (pure deterministic logic against the existing
Formula DSL parser), and the three LLM-backed features fail with a clear, actionable 503 message
rather than crashing or silently doing nothing.

## Architecture

`src/girp/ai/provider.py` defines the abstraction: an `AIProvider` protocol with a single
`complete(prompt, system=None) -> str` method, three real implementations
(`AnthropicProvider`, `OpenAIProvider`, `GeminiProvider`) each using the lazy-import pattern
already established by `YFinanceProvider` (the corresponding SDK is imported inside `__init__`,
not at module load time, so the app runs fine with none of `anthropic`/`openai`/
`google-generativeai` installed), and an `UnconfiguredProvider` whose `complete()` always raises
`AIProviderNotConfigured` naming all three supported environment variables. `get_provider()` picks
a provider by checking `ANTHROPIC_API_KEY` → `OPENAI_API_KEY` → `GEMINI_API_KEY` in that order,
falling back to `UnconfiguredProvider()` if none are set.

`src/girp/ai/formula_explainer.py` is deliberately independent of the provider abstraction --
it needs no LLM call at all. `FIELD_DESCRIPTIONS` is a dict of every technical, fundamental,
valuation, composite-score, and classification field name this app exposes (close, sma_20,
rsi_14, macd, adx_14, pe, roe, piotroski_f_score, graham_number, score_overall, sector, ...) with
an English and Thai label for each. `explain_formula()` parses a formula with the existing
`parse_formula()` and walks the resulting `Formula`/`Comparison` dataclasses to build a plain
sentence ("This screens for stocks where closing price (close) is greater than 20-period simple
moving average and ..."). `debug_formula()` also calls the real parser: on a `ParseError` it
inspects the raw source for the two most common mistakes (parentheses, which this DSL's flat
AND/OR grammar doesn't support, and missing quotes around text values) and runs `difflib` typo
matching against known field names; on a successful parse it separately checks the left-hand
field of every comparison *and* any bare (unquoted) right-hand identifier against
`FIELD_DESCRIPTIONS`, so both `close > sma_2O` (typo) and `sector = Technology` (missing quotes)
are caught even though both parse without error.

`src/girp/ai/service.py`'s `AIService` wraps a provider (constructor-injected for testability,
defaults to `get_provider()`) and exposes six methods. `explain_formula`/`debug_formula` just
delegate to the module above -- no provider involved. `summarize`, `compare`, `suggest_strategy`,
and `optimize_strategy` build a prompt from the caller's data (a symbol's merged
technicals+fundamentals, two-or-more symbols' metrics side by side, a free-text goal, or a
formula plus its backtest metrics) and call `self._provider.complete(prompt, system=...)`. The
shared system prompt (English/Thai) tells the model it's embedded in this specific app, to stay
grounded in the numbers given, never give direct buy/sell advice, and that this app's formula
language only supports a flat AND/OR chain with no parentheses -- so any formula the model
proposes back (in Suggest/Optimize Strategy) is actually usable in Screener/Ranking/Backtest
without translation.

Six endpoints in `src/girp/api/main.py`: `POST /ai/explain-formula`, `/ai/debug-formula` (both
functional with zero configuration), and `/ai/summarize`, `/ai/compare`, `/ai/suggest-strategy`,
`/ai/optimize-strategy` (each catching `AIProviderNotConfigured` and returning HTTP 503 with the
underlying message, and catching any other `RuntimeError` from a misconfigured/failing SDK call
as a 502). A `get_ai_service()` factory (mirroring `get_service()`/`get_watchlist_service()`)
makes the dependency swappable in tests.

## Implementation

- `src/girp/ai/provider.py` (new) -- `AIProvider` protocol, `AIProviderNotConfigured`,
  `AnthropicProvider`/`OpenAIProvider`/`GeminiProvider`/`UnconfiguredProvider`, `get_provider()`.
- `src/girp/ai/formula_explainer.py` (new) -- `FIELD_DESCRIPTIONS`, `explain_formula()`,
  `debug_formula()`, `DebugResult` dataclass.
- `src/girp/ai/service.py` (new) -- `AIService`.
- `src/girp/ai/__init__.py` (new) -- re-exports the above.
- `src/girp/api/main.py` -- `get_ai_service()` + six `/ai/*` routes; root endpoint listing updated.
- Frontend: `frontend/src/api.js` gained `aiExplainFormula`/`aiDebugFormula`/`aiSummarize`/
  `aiCompare`/`aiSuggestStrategy`/`aiOptimizeStrategy`. `frontend/src/pages/AiPage.jsx` (new) has
  four sections matching the four requested features; Summary/Compare auto-fetch technicals+
  fundamentals for the entered symbol(s) via existing endpoints before calling the AI endpoint,
  and Optimize Strategy auto-runs a backtest before calling the AI endpoint, so the user only
  types a symbol/formula/goal rather than hand-assembling a metrics payload. Every LLM-backed
  section shows a friendly "AI not configured" message (via a small `isNotConfiguredError()`
  check on the thrown error text) instead of a raw error when the backend returns 503.
  `App.jsx` gained an `ai` tab; `translations.js` gained `nav.ai` and a full `ai.*` tree (EN+TH).

## Why a provider-agnostic scaffold now, no key yet

The user does not currently have an Anthropic/OpenAI/Gemini API key and asked explicitly to have
the scaffold built first ("ยังไม่มี key ตอนนี้ - สร้างโครงไว้ก่อน"). Rather than hardcoding one
vendor, `get_provider()`'s env-var precedence means the app "just works" the moment any one of the
three keys is set on the server (`export ANTHROPIC_API_KEY=...` before starting the backend, no
code changes) -- and continues to run today, with Formula Explain/Debug fully functional and the
other three features failing informatively instead of being half-built or crashing.

## Unit tests

35 new tests (151 total, up from 116):

- `tests/test_ai_provider.py` -- `get_provider()`'s env-var precedence (Anthropic over OpenAI
  over Gemini, falling back to `UnconfiguredProvider` with none set), and that
  `UnconfiguredProvider().complete()` raises `AIProviderNotConfigured` naming all three env vars.
- `tests/test_ai_formula_explainer.py` -- `explain_formula()` correctness in English and Thai
  (including quoted text values and multi-condition AND chains) and that it still raises
  `ParseError` for genuinely invalid syntax; `debug_formula()` correctness for valid formulas,
  parentheses (DSL doesn't support them), field-name typos (via difflib suggestion), unquoted
  text values, and unknown field names.
- `tests/test_ai_service.py` -- `explain_formula`/`debug_formula` on `AIService` work with the
  default `UnconfiguredProvider`; `summarize` raises `AIProviderNotConfigured` when unconfigured
  and correctly calls an injected fake provider (dependency injection, no real API key needed) for
  all four LLM-backed methods, checking the built prompt actually contains the caller's data.
- `tests/test_api_ai.py` -- `ai_explain_formula`/`ai_debug_formula` handlers work end-to-end with
  the real default `get_ai_service()` (no key set in the test environment) and return 400 on a bad
  formula; the four LLM-backed handlers return 503 by default and succeed once `get_ai_service` is
  monkeypatched to return an `AIService` wrapping a fake provider, following the same
  monkeypatch-the-module-level-factory pattern as `tests/test_api_technicals.py`.

Full backend suite (151 tests) passes. Frontend build verified via the standard rsync-into-`/tmp`
+ `npm run build` workflow; EN/TH translation parity confirmed at 358/358 keys (up from 331).

## Integration test

Manually exercised `AIService(provider=UnconfiguredProvider())` end-to-end: `explain_formula`/
`debug_formula` returned correct output with zero configuration, while `summarize`/`compare`/
`suggest_strategy`/`optimize_strategy` all raised `AIProviderNotConfigured`. Manually exercised the
same four methods with an injected fake provider to confirm each builds a prompt containing the
caller's actual symbol/metrics/goal/formula data and returns the provider's response unchanged.
Confirmed via `debug_formula("close > sma_2O")` (letter O, not zero) and
`debug_formula("sector = Technology")` (missing quotes) that both known real-world mistakes are
caught with an actionable suggestion, not just a generic parser error.

## What this is not (yet)

- No real LLM call has been made against a live API in this session -- the user has no key
  configured yet, so `AnthropicProvider`/`OpenAIProvider`/`GeminiProvider` are exercised only via
  `__init__`-patched unit tests, not a real network round-trip. The first real run should be
  spot-checked once a key is set.
- The `anthropic`/`openai`/`google-generativeai` Python packages are not installed in this
  environment (deliberately, to keep the scaffold dependency-free until a key exists) -- installing
  the relevant one is a `pip install` away when a key is added; `get_provider()` will start
  returning that real provider automatically, no code change needed.
- Formula Suggest/Optimize responses are free-text from the LLM, not auto-validated against
  `parse_formula()` -- a user copying a model-suggested formula into Screener/Ranking/Backtest may
  still hit an "Explain/Debug" formula error if the model strays from the flat AND/OR grammar
  despite the system prompt describing it; wiring "Debug this suggested formula" as a one-click
  follow-up was considered but left for a future phase to keep this one scoped.
- No conversation memory/chat history -- every AI call in this phase is a single, stateless
  prompt/response; there's no multi-turn "AI chat" experience.

## Phase 10 addendum -- API key entry & save UI (2026-07-29)

The initial Phase 10 scaffold relied entirely on server environment variables
(`ANTHROPIC_API_KEY` etc.), which is fine for a developer but leaves no in-app way for GUM to
paste a key without editing server config. This addendum adds a save-in-the-app option on top of
the existing scaffold, without removing the env-var path.

### Architecture

A new single-row `ai_settings` table in `SQLiteCache` (`src/girp/storage/sqlite_cache.py`) holds
one saved `provider`/`api_key`/`model` (id fixed at 1, `INSERT ... ON CONFLICT(id) DO UPDATE`, so
"save" always just overwrites the previous entry -- there is exactly one active AI configuration
at a time, matching how `get_provider()`'s env-var precedence already only ever picks one
provider). `save_ai_settings()`/`get_ai_settings()`/`delete_ai_settings()` were added alongside
the existing `upsert_watchlist`-style methods.

The tricky part: `get_ai_service()` (the factory used by every `/ai/*` route) cannot eagerly
construct the real provider (`AnthropicProvider(...)` etc.) just because settings were saved --
that would import the provider's SDK immediately, and if the user saved a key before running
`pip install anthropic`, even `/ai/explain-formula` (which needs no LLM at all) would break. To
solve this, `src/girp/ai/provider.py` gained `LazyProvider`, a thin wrapper holding the
provider name/key/model and only calling the existing `build_provider()` factory (which does the
real SDK import) the first time `.complete()` is actually invoked. `get_ai_service()` now checks
`SQLiteCache.get_ai_settings()` first and wraps a match in `LazyProvider`; only if nothing was
saved does it fall back to the original `get_provider()` (env vars), matching the priority order
GUM would expect: explicit in-app save beats server environment configuration.

Three new endpoints: `GET /ai/settings` (returns `configured`, `source` -- `"saved"` or `"env"` --
`provider`, a masked `api_key_masked` like `************1234`, `model`, `updated_at`; never
returns the raw key), `POST /ai/settings` (`{provider, api_key, model?}`; validates `provider` is
one of `anthropic`/`openai`/`gemini` and `api_key` is non-empty, then saves -- deliberately does
**not** try to construct the real provider at save time, for the same lazy-import reason above),
and `DELETE /ai/settings` (clears the saved row, falling back to env vars if any are set).

### Implementation

- `src/girp/storage/sqlite_cache.py` -- `ai_settings` table + 3 methods.
- `src/girp/ai/provider.py` -- `PROVIDER_CLASSES` dict, `build_provider(name, key, model=None)`
  factory, `LazyProvider` class.
- `src/girp/ai/__init__.py` -- exports the three additions above.
- `src/girp/api/main.py` -- `_ai_settings_cache()` helper, `get_ai_service()` rewritten to prefer
  saved settings, `_mask_api_key()`, `ai_get_settings`/`ai_save_settings`/`ai_delete_settings`
  handlers; root endpoint listing gained `ai_settings`.
- Frontend: `frontend/src/api.js` gained `getAiSettings`/`saveAiSettings`/`deleteAiSettings`.
  `frontend/src/pages/AiPage.jsx` gained a `SettingsSection` at the top of the AI tab: a provider
  dropdown (Anthropic/OpenAI/Gemini), a password-style API key field with a "show key" checkbox,
  an optional model override field, Save and Clear buttons, and a status line showing whether a
  key is saved (masked) or coming from an env var, or nothing is configured. `translations.js`
  gained the `ai.settings.*` tree (EN+TH, including two message-formatting entries,
  `statusSaved`/`statusEnv`, using the existing `t(path, ...args)` function-value convention
  already used elsewhere, e.g. `watchlists.saved`).

### Unit tests

22 new tests (173 total, up from 151):

- `tests/test_ai_settings_storage.py` -- round-trips provider/key/model through
  `SQLiteCache.save_ai_settings`/`get_ai_settings`, confirms re-saving overwrites rather than
  duplicating, and confirms `delete_ai_settings()`'s boolean return in both cases.
- `tests/test_ai_lazy_provider.py` -- `build_provider()` dispatches to the right class and passes
  `model` through only when given, raises `ValueError` for an unknown provider name;
  `LazyProvider` does **not** touch the real provider class at construction time, builds it (and
  calls through to it) only on the first `complete()` call, builds only once across repeated
  calls, and -- run against the real (not-installed-in-this-environment) `anthropic` package --
  confirms the expected `RuntimeError` surfaces lazily rather than at `LazyProvider.__init__`.
- `tests/test_api_ai_settings.py` -- the full save/get/delete lifecycle through the actual route
  handlers (using an in-memory `SQLiteCache` monkeypatched onto `api_main._ai_settings_cache`,
  same pattern as `test_api_technicals.py`'s `get_service` monkeypatching); confirms saving
  succeeds even though the `anthropic` SDK isn't installed in this environment (the key point of
  the lazy design); confirms `get_ai_service()` picks up saved settings as a `LazyProvider`; and
  crucially confirms `/ai/explain-formula` still returns a correct answer even with a
  SDK-less provider saved (502, not a crash, only shows up on `/ai/summarize`, which actually
  needs the LLM).

Full backend suite (173 tests) passes. Frontend build verified via the standard rsync-into-`/tmp`
+ `npm run build` workflow; EN/TH translation parity confirmed at 372/372 keys (up from 358).

### Integration test

Manually drove the full lifecycle through the route handlers directly: `GET /ai/settings` on an
empty store reports `configured: false`; `POST /ai/settings` with `{provider: "anthropic",
api_key: "sk-ant-test-1234"}` succeeds and returns a masked key; a follow-up `GET` reports
`configured: true, source: "saved"`; `POST /ai/explain-formula` still returns a correct plain-
language explanation even with that (SDK-less) provider saved; `POST /ai/summarize` against the
same saved settings correctly surfaces a 502 (SDK not installed) rather than a 503 (not
configured) or an unhandled crash, confirming the settings are actually being read and the
distinction between "nothing configured" and "configured but SDK missing" is preserved; `DELETE
/ai/settings` clears the row and a final `GET` reports `configured: false` again.

### What this is not (yet)

- Saving does not validate the key against the real provider's API (no network call is made at
  save time, by design -- see the lazy-import rationale above) -- a mistyped or revoked key will
  only surface as an error the first time an LLM-backed feature is actually used, not at save
  time. A "test connection" button was considered but left out to keep this addendum scoped; it
  would need the corresponding SDK installed to be meaningful anyway.
- The saved API key is stored in plaintext in the local SQLite cache file (`data/girp_cache.
  sqlite3`), consistent with how this file already stores everything else this app caches --
  there is no separate secrets vault or OS keychain integration. Anyone with file access to that
  SQLite database can read the key back out.
- Only one AI configuration is stored at a time (matching `get_provider()`'s single-provider env
  var precedence) -- there's no way to save multiple keys and switch between them without
  re-entering a key each time.
