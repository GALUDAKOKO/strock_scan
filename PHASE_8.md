# GIRP Phase 8 — Composite ranking scores + richer backtest metrics

Phase 8 closes two more gaps from the master-plan reconciliation: Ranking only sorted by a
single raw metric (no Quality/Growth/Value/Momentum/Risk/Overall composite), and Backtest only
reported total return and max drawdown (no CAGR, Sharpe ratio, win rate, profit factor,
commission, or slippage).

## Architecture

**Composite ranking scores** (`src/girp/ranking/composite.py`): a cross-sectional percentile-rank
scorer. For every symbol being ranked in the same `/rank` call, each factor (e.g. `roe`, `pe`,
`momentum_score`) is converted to a 0-100 percentile against the other symbols in that batch —
not against some fixed universe-wide benchmark, since GIRP has no persistent "all stocks"
universe to benchmark against (see the Phase 6 note on watchlists). "Lower is better" factors
(PE, PBV, debt-to-equity, ATR%) are inverted before averaging. Five categories are computed
this way, then averaged into an overall score:

| Score | Factors used |
|---|---|
| `score_quality` | ROE, ROA, ROIC, net margin, current ratio |
| `score_growth` | Revenue growth, asset growth |
| `score_value` | PE, PBV (inverted -- cheaper scores higher) |
| `score_momentum` | momentum_score, close vs SMA-20, close vs EMA-20 |
| `score_risk` | Debt-to-equity, ATR as % of price (inverted -- lower risk scores higher) |
| `score_overall` | Average of whichever of the five categories have data |

A symbol missing every factor in a category gets `None` for that category rather than a
misleading default (e.g. a stock with zero fundamentals data gets `score_quality = None`, not 0
or 50). `RankingService.rank()` now runs in two passes: first it fetches history/fundamentals
for every symbol and builds each one's metrics dict, then it computes composite scores across
the whole batch and merges them back into every symbol's metrics *before* the filter formula and
sort key are applied -- so `score_overall` (or any other composite score) can be used directly as
`sort_by`, and can even appear inside a filter formula (e.g. `score_quality > 60 AND pe < 20`).

**Backtest metrics** (`src/girp/backtesting/service.py`): `BacktestService.run()` gained two new
parameters, `commission_pct` and `slippage_pct` (both default to `0`, so existing behavior is
unchanged unless a caller opts in). Slippage worsens the execution price (buys fill higher,
sells fill lower); commission is deducted from cash on both entry and exit. Every trade's
recorded `price` is now the actual (slippage-adjusted) execution price, so downstream reporting
reflects real fill quality. Three new metrics are computed from the equity curve and trade log:

- **CAGR** -- annualized return from `initial_cash` to `final_equity` over the elapsed calendar
  days between the first and last candle (`None` if equity is non-positive or the elapsed time
  isn't positive).
- **Sharpe ratio** -- from daily equity-curve returns, annualized by `sqrt(252)` (`None` when
  there are fewer than 2 return observations or their variance is zero, i.e. a flat equity curve
  that never traded).
- **Win rate / profit factor / win count / loss count** -- computed from completed round trips
  (each BUY paired with its following SELL). Profit factor is gross profit over gross loss;
  `None` when no round trip has completed yet.

## Implementation

- `RankingService.rank()`: two-pass restructure (see above), fully additive to `RankingResult.metrics`.
- `BacktestService.run()`: `commission_pct`/`slippage_pct` params, `Trade.price` now means
  execution price (post-slippage), `BacktestResult` gained `cagr_pct`, `sharpe_ratio`,
  `win_rate_pct`, `profit_factor`, `win_count`, `loss_count`, `commission_pct`, `slippage_pct`.
- API (`src/girp/api/main.py`): `/backtest` accepts `commission_pct`/`slippage_pct` in the
  payload (both default `0`); `_backtest_result_to_dict` surfaces all the new fields.
  `/rank`'s response needed no changes -- composite scores ride along inside `metrics` the same
  way every other metric already does.
- Frontend: Ranking page gained `score_overall`/`score_quality`/`score_growth`/`score_value`/
  `score_momentum`/`score_risk` as both sortable options and result-table columns (sorting by any
  `score_*` field or PE/ROE/etc. auto-enables `include_fundamentals`, same as before). Backtest
  page gained commission/slippage input fields and CAGR/Sharpe/win-rate/profit-factor in the
  summary table, detail cards, and HTML/PDF export.

## Unit tests

22 new tests, all hand-verified against concrete numbers or shape-based invariants (no
mocked expectations copied from the implementation itself):

- `tests/test_composite_scores.py` (8 tests) -- higher ROE scores higher quality, lower PE scores
  higher value, lower debt/ATR scores higher risk, missing fundamentals yield `None` (not a
  default), overall is the average of available categories, a single symbol gets the neutral
  50th percentile, tied values share a percentile, empty input returns `{}`.
- `tests/test_backtest_metrics.py` (12 tests) -- zero commission/slippage matches prior exact
  fill behavior, commission reduces final equity, slippage worsens the recorded buy price by
  exactly the configured percentage, negative commission/slippage is rejected, CAGR is positive
  on a steady uptrend, Sharpe ratio is `None` on a flat (never-traded) equity curve and positive
  on a steady uptrend, win rate/profit factor match a hand-counted win/loss tally on a choppy
  synthetic series, and both are `None` when no round trip completes.
- `tests/test_ranking_service.py` gained 2 tests confirming composite scores are merged into
  every result's `metrics` and that `sort_by="score_overall"` actually re-orders results.

All 111 backend tests pass (up from 91 before this phase). Frontend build and EN/TH translation
parity (232/232 keys) both verified.

## What this is not (yet)

- Composite scores are always computed (cheap, pure arithmetic on data already fetched) but are
  only meaningful when multiple symbols are ranked together and at least some of them have
  fundamentals data. Ranking a single symbol still works, but every category collapses to the
  neutral 50th percentile since there's nothing to compare against.
- No persistent "market-wide" percentile benchmark -- scores are always relative to the current
  batch, not a fixed universe. This matches how watchlists work in this app (see PHASE_6.md) but
  means the same stock can get a different `score_quality` depending on which peers it's ranked
  against.
- Sharpe ratio uses a flat 0% risk-free rate and assumes daily bars (annualizing by `sqrt(252)`);
  it isn't adjusted for other intervals like weekly or monthly data yet.
