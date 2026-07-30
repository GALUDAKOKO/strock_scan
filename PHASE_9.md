# GIRP Phase 9 — Screening Engine classification filters

Phase 9 closes the last open item in Phase 7 Screening Engine from the master-plan
reconciliation: filtering by Market/Exchange/Sector/Industry/Country/Asset-type. It also fixes
a translation bug found while wiring this up (see "Bug fixed" below).

## Architecture

`Asset` (`src/girp/domain/models.py`) gained four new fields: `sector`, `industry`, `country`,
`exchange` (all `str | None`, default `None`). The `assets` SQLite table gained matching columns.
Because a cache file may already exist on disk from before this phase, `SQLiteCache.initialize()`
now runs an idempotent `_migrate_asset_classification_columns()` step that `ALTER TABLE`s in any
missing column -- safe to run on every startup, no-ops once the columns exist.

`YFinanceProvider.get_info()` now reads `sector`, `industry`, `country`, and
`fullExchangeName`/`exchange` out of `ticker.info` alongside the fields it already populated.

Rather than inventing a new filter mechanism, this phase leans on something already built: the
Formula DSL's `=`/`!=` operators already support quoted string comparisons (`market = "SET"` was
in `test_formula_evaluator.py` since Phase 1). So `ScreeningService.screen()` and
`RankingService.rank()` now merge each symbol's classification fields into its `metrics` dict
(`market`, `asset_type`, `sector`, `industry`, `country`, `exchange`) via a new
`_classification_metrics()` helper -- unconditionally, not gated behind `include_fundamentals`,
since it's one cheap cached `get_info()` call per symbol. This means `sector = "Technology"`,
`country = "Thailand"`, or `exchange = "NASDAQ"` all work as filter conditions or as parts of a
formula immediately, with no new API surface.

## Implementation

- `src/girp/domain/models.py`: `Asset` +4 fields.
- `src/girp/storage/sqlite_cache.py`: `assets` table +4 columns, migration helper, `upsert_asset`/`get_asset` updated.
- `src/girp/providers/yfinance_provider.py`: `get_info()` populates the new fields.
- `src/girp/screening/service.py`, `src/girp/ranking/service.py`: `_classification_metrics()` helper, merged into every symbol's metrics.
- `src/girp/api/main.py`: `_asset_to_dict()` (used by `GET /assets/{symbol}`) now returns `sector`/`industry`/`country`/`exchange`. `/screen` and `/rank` needed no changes -- the new fields ride along inside `metrics` the same way every other metric already does.
- Frontend: `frontend/src/filters.js` gained `SECTORS` (Yahoo Finance's own sector taxonomy, not
  strict GICS wording, so the values match real `sector` data exactly) and `ASSET_TYPES` (the
  lowercased `quoteType` values yfinance returns). `FilterPanel.jsx` gained a "Classification"
  group with two `<select>` dropdowns (Sector, Asset type) rather than checkboxes for these two
  fields specifically.

### Why dropdowns instead of checkboxes for sector/asset-type

The existing Formula DSL has no support for parenthesized grouping or `(A OR B) AND C` --
comparisons are joined into one flat left-to-right AND/OR chain (see `parse_formula`). Since a
stock's `sector` can only ever equal one value, multi-select checkboxes AND-joined together
(the pattern every other filter group uses) would produce an impossible condition
(`sector = "Technology" AND sector = "Energy"`, which never matches anything). A single-select
dropdown sidesteps the problem entirely: at most one `sector = "..."` clause is ever added to
the formula, so it composes correctly with every other AND-joined filter.

### Why country/industry/exchange are not checkboxes

Sector (11 values) and asset type (7 values) are small, bounded, standardized vocabularies --
reasonable as a dropdown. Country, industry, and exchange are effectively open-ended (hundreds of
distinct values across a real universe of stocks), so hardcoding a checkbox or dropdown list for
them would either be incomplete or a huge, unmaintainable list. Since the underlying fields are
already available in every symbol's metrics (see above), they're reachable today by typing
directly into the existing custom-formula box, e.g. `country = "Thailand"` or
`exchange = "NASDAQ"` -- no separate free-text UI was added because the custom-formula input
already does this job. A hint under the Classification group in the Screener/Ranking pages says
so explicitly.

## Bug fixed along the way

While wiring up the Classification group, a real UI bug from the Phase 3 Technical Engine work
was found: `frontend/src/filters.js`'s `TECHNICAL_FILTERS` array carries a `label` field, but
`FilterPanel.jsx`'s `FilterGroup` component actually renders `t(\`filters.${filter.id}\`)`, not
`filter.label`. The 16 technical filter presets added when MACD/ADX/Bollinger/CCI/MFI/Supertrend/
candlestick-pattern indicators were exposed (`macd_bullish`, `adx_strong_trend`,
`bollinger_breakout_up`, etc.) never got matching `filters.<id>` translation keys added, so those
checkboxes were rendering the raw untranslated key path as their visible label. Both `translations.en.filters`
and `translations.th.filters` now have all 16 keys filled in.

## Unit tests

5 new tests (116 total, up from 111):

- `tests/test_sqlite_cache.py` -- round-trips the new classification fields, confirms they
  default to `None` when unset, and (the most important one) simulates a database created
  *before* this phase existed -- a bare `assets` table with only the original six columns -- to
  prove the migration adds the missing columns without raising or losing existing rows.
- `tests/test_screening_service.py` -- confirms classification fields land in every result's
  `metrics`, and that `sector = "Technology"` actually filters results end-to-end through
  `ScreeningService.screen()`.

Frontend build and EN/TH translation parity (254/254 keys, including the Phase 3 bug fix) both
verified.

## Integration test

Verified end-to-end with a fake provider returning different sectors per symbol, screening a
two-symbol batch with `sector = "Technology"` and confirming only the matching symbol passes.
Confirmed the migration path against a hand-built pre-Phase-9 schema (dropped and recreated the
`assets` table without the new columns, inserted a row, then re-ran `initialize()` and verified
both the old row survives and the new columns exist with `NULL` values for it).

## What this is not (yet)

- Timeframe filtering (from the original Phase 7 checkbox list) is not part of this phase --
  `/screen` and `/rank` already accept `interval` as a request parameter (`1d`, `1wk`, etc.), so
  "timeframe" was really a request-level setting rather than a per-symbol filterable field; no
  further UI work was identified as missing there.
- Classification data quality depends entirely on what `yfinance`/Yahoo Finance reports for a
  given symbol -- some tickers (especially non-US, delisted, or thinly-covered ones) may have
  `None` for sector/industry/country, in which case they simply won't match any classification
  filter (consistent with how missing fundamentals already behave elsewhere in this app).
