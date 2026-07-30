# 20_ROADMAP

Milestones.

## Status
Authoritative.

## Master plan reconciliation (2026-07-23)

GUM's master plan defines Phase 0-11. This project's PHASE_1.md-PHASE_6.md were built
before that plan existed, under different numbering. This section maps one to the other so
nothing gets rebuilt by accident, and lists what the master plan calls for that does not
exist yet.

| Master plan phase | Maps to | Status |
|---|---|---|
| Phase 0 Foundation | PHASE_1.md (partial) | FastAPI, React, SQLite done. Config/env management, structured logging, formal DI container, a generic plugin loader, GitHub Actions, Docker, Render deploy: **not built**. |
| Phase 1 Data Engine | PHASE_1.md + **PHASE_9.md (done, 2026-07-23)** | yfinance provider, SQLite cache, refresh, history, financial statements done. Market/Exchange/Sector/Industry/Country now first-class `Asset` fields (with an idempotent migration for pre-existing on-disk caches). |
| Phase 2 Fundamental Engine | PHASE_5.md | PE, PBV, ROE, ROA, ROIC, EPS, revenue growth, debt-to-equity, FCF, owner earnings, dividend yield, Piotroski, Altman, Beneish done. PEG ratio and an explicit "Buffett score": **not built**. Not implemented as a loadable plugin registry -- plain functions today. |
| Phase 3 Technical Engine | PHASE_2.md + **PHASE_7.md (done, 2026-07-23)** | SMA, EMA, RSI, momentum_score, MACD, ADX, ATR, CCI, MFI, OBV, VWAP, Bollinger, Ichimoku, Supertrend, candlestick patterns (doji/hammer/shooting star/engulfing), rolling support/resistance and floor pivots all built and wired additively into `summarize_history()` -- `/screen` and `/rank` pick them up with zero other code changes. A dedicated `GET /assets/{symbol}/technicals` endpoint (added alongside the Asset Detail page) also exposes the full set directly. 91 backend unit tests. Remaining gap: Ichimoku spans aren't forward-displaced for charting, periods aren't configurable per-request. `knowledge/*.md` stub docs still need their formulas filled in as a documentation-only follow-up. |
| Phase 4 Valuation Engine | PHASE_5.md | DCF, Graham, margin of safety, fair value done. Explicit upside/downside/risk/gap framing: partially covered by margin-of-safety %, not broken out separately. |
| Phase 5 Formula DSL | PHASE_1.md | Parser + evaluator (comparisons joined by AND/OR) done; the checkbox `FilterPanel` is a first visual builder, plus a copy-pasteable formula reference table on the Backtest page. No separate lexer module, no optimizer, no drag-and-drop visual builder. |
| Phase 6 Ranking Engine | PHASE_3.md + **PHASE_8.md (done, 2026-07-23)** | Ranking by any single metric works. Composite Quality/Growth/Value/Momentum/Risk/Overall scores **done**: cross-sectional percentile-rank scoring across the current batch, merged into every result's `metrics` and usable as `sort_by` or inside filter formulas. Gap: scores are relative to the current ranked batch, not a persistent universe-wide benchmark (no such universe exists in this app -- see the Phase 6/watchlists note above). |
| Phase 7 Screening Engine | PHASE_2.md + **PHASE_9.md (done, 2026-07-23)** | Formula-based screening with checkbox presets works. Sector and Asset-type are dropdown filters (single-select, since the Formula DSL has no `(A OR B)` grouping and a stock can only have one sector); Market/Exchange/Country/Industry are reachable via the existing custom-formula box (`country = "Thailand"`, `exchange = "NASDAQ"`) since those fields are open-ended and don't suit a fixed checkbox list. Timeframe is already a request-level `interval` parameter, not a per-symbol filter. |
| Phase 8 Backtest | PHASE_4.md + **PHASE_8.md (done, 2026-07-23)** | Long-only formula backtest, equity curve, total return, max drawdown, trade log done. Commission, slippage, CAGR, win rate, Sharpe ratio, profit factor all **done** and exposed via `/backtest` + the Backtest page (summary table, detail cards, HTML/PDF export). |
| Phase 9 Frontend | (this codebase, `frontend/`) | Tab nav, tables, checkbox formula builder, export to HTML/PDF, EN/TH i18n, watchlists (with CSV/XLSX import) done. Price charts (dependency-free SVG) and an Asset Detail page **done**. Manual dark-mode toggle (currently follows OS `prefers-color-scheme` only), a sidebar layout, and tested responsive/mobile breakpoints: **not built**. |
| Phase 10 AI Layer | **PHASE_10.md (done, 2026-07-29)** | Provider-agnostic scaffold (Anthropic/OpenAI/Gemini/Unconfigured, env-var precedence, lazy SDK imports) plus all four requested features: Formula Explain & Debug (deterministic, no LLM/key needed -- works today), AI Summary, AI Compare, and Strategy Suggest & Optimize (all three require a configured provider; gracefully return HTTP 503 with an actionable message when none is set). Six `/ai/*` endpoints + an AI tab in the frontend. **Addendum (same day):** in-app API key entry/save UI -- `GET/POST/DELETE /ai/settings`, a `SettingsSection` on the AI tab (provider dropdown, key field, optional model, save/clear), and `LazyProvider` so a saved key never breaks the SDK-free Explain/Debug endpoints even before the corresponding SDK package is installed. Saved settings take priority over env vars. Gap: no real LLM call has been exercised against a live API yet since the user has no key configured -- only unit-tested via dependency injection; no conversation memory (single-turn only); AI-suggested formulas aren't auto-validated against the parser before being shown to the user; saved API key is stored in plaintext in the local SQLite cache file, no OS keychain integration. |
| Phase 11 Release | -- | 173 backend unit tests exist; 0 frontend tests. No auth, no Docker, no CI, no Render deploy, no user docs beyond the PHASE_N.md files and Swagger UI. |

## Process going forward

Per GUM's request, every future phase of new work should follow:
Architecture -> Implementation -> Unit Test -> Integration Test -> Documentation -> Demo,
and land as its own PHASE_N.md, same as Phases 1-6.
