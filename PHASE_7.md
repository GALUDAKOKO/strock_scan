# GIRP Phase 7 — Technical Engine (complete)

Phase 7 fills in the biggest gap identified in `architecture/20_ROADMAP.md`'s master-plan
reconciliation: the Technical Engine only had SMA, EMA, RSI, and a composite momentum score.
This phase adds the full indicator set GUM asked for — MACD, Bollinger Bands, ATR, ADX, CCI,
MFI, OBV, VWAP, Ichimoku, Supertrend, candlestick patterns, and support/resistance — and wires
every one of them directly into `/screen` and `/rank` with zero API or service-layer changes.

## Architecture

All new indicators live under `src/girp/technical/` as pure functions on `Decimal` values or
`Candle` lists, matching the existing style in `indicators.py`:

- `volatility.py` — `true_range`, `true_range_series`, `atr_series`, `atr` (Wilder's smoothing),
  `bollinger_bands` (middle/upper/lower/%B), `adx` (with `+DI`/`-DI`)
- `oscillators.py` — `ema_series` (internal helper: full EMA series, not just the latest scalar),
  `macd` (line/signal/histogram), `cci` (Commodity Channel Index)
- `volume.py` — `obv` (On-Balance Volume), `vwap` (Volume-Weighted Average Price), `mfi` (Money
  Flow Index)
- `trend.py` — `ichimoku` (tenkan/kijun/senkou A/senkou B/chikou, latest values, no forward
  displacement), `supertrend` (ATR-based trailing band with direction flip), `pivot_points`
  (classic floor pivots from the prior bar), `rolling_support_resistance` (rolling high/low)
- `patterns.py` — `doji`, `hammer`, `shooting_star`, `bullish_engulfing`, `bearish_engulfing`,
  `detect_patterns`. Every pattern returns a `Decimal("1")`/`Decimal("0")` flag rather than a
  Python bool, so they compare cleanly against numeric literals in the Formula DSL (e.g.
  `pattern_doji > 0`)

Every function degrades gracefully to `None` (or all-`None` fields in a dict) when there isn't
enough history yet, the same convention `sma()`/`rsi()` already used. Nothing raises except on
programmer error (a non-positive `period`).

## Implementation — wiring into `/screen` and `/rank`

`indicators.py`'s `summarize_history()` is the single place the screening and ranking services
pull metrics from. Phase 7 extends it additively — every existing key (`close`, `sma_20`,
`rsi_14`, `momentum_score`, ...) is untouched, so no other code needed to change. The new keys
available in every formula and result row:

| Key | Meaning |
|---|---|
| `atr_14` | Average True Range (14, Wilder) |
| `bollinger_middle_20` / `bollinger_upper_20` / `bollinger_lower_20` / `bollinger_percent_b_20` | Bollinger Bands (20, 2 std dev) |
| `adx_14` / `plus_di_14` / `minus_di_14` | Average Directional Index and directional indicators |
| `macd` / `macd_signal` / `macd_histogram` | MACD (12/26/9) |
| `cci_20` | Commodity Channel Index (20) |
| `obv` | On-Balance Volume (cumulative over the fetched history) |
| `vwap` | Volume-Weighted Average Price (over the fetched history) |
| `mfi_14` | Money Flow Index (14) |
| `ichimoku_tenkan_sen` / `ichimoku_kijun_sen` / `ichimoku_senkou_span_a` / `ichimoku_senkou_span_b` / `ichimoku_chikou_span` | Ichimoku Cloud components |
| `supertrend` / `supertrend_direction` | Supertrend line and direction (`1` up / `-1` down) |
| `pivot` / `pivot_r1` / `pivot_r2` / `pivot_s1` / `pivot_s2` | Classic floor pivot levels |
| `support_20` / `resistance_20` | Rolling 20-bar support/resistance |
| `pattern_doji` / `pattern_hammer` / `pattern_shooting_star` / `pattern_bullish_engulfing` / `pattern_bearish_engulfing` | Candlestick pattern flags (1/0) |

Example formulas now possible without any backend change:

```
macd > macd_signal AND adx_14 > 25
close > bollinger_upper_20 AND mfi_14 > 80
pattern_bullish_engulfing > 0 AND close > support_20
supertrend_direction > 0 AND cci_20 < -100
```

The frontend's Screener/Ranking filter checkboxes (`frontend/src/filters.js`) were extended with
presets for the most commonly used new signals (MACD cross, ADX strong-trend, Bollinger breakout,
CCI/MFI overbought/oversold, Supertrend direction, engulfing candles) so they're one click away —
no need to hand-type formulas to use them.

## Unit tests

89 backend unit tests pass (up from 53 before this phase), including new suites:

- `tests/test_volatility.py` — true range, ATR (hand-verified on constant-range data), Bollinger
  Bands (hand-verified against the closed-form population std-dev of 1..20), ADX directional bias
  on synthetic up/down trends
- `tests/test_oscillators.py` — EMA series seeding, MACD on flat/uptrending series (hand-verified
  that a constant series yields exactly zero MACD/signal/histogram), CCI on flat and breakout bars
- `tests/test_volume.py` — OBV (hand-verified cumulative sum), VWAP (hand-verified weighted
  average), MFI on all-up/all-down synthetic series
- `tests/test_trend.py` — Ichimoku on a flat series (every component collapses to the same
  midpoint, hand-verifiable), pivot points (hand-verified against the classic floor-pivot
  formula), rolling support/resistance, Supertrend direction on synthetic trends
- `tests/test_patterns.py` — doji/hammer/shooting-star shape detection with explicit
  open/high/low/close values chosen to hit or miss each threshold, bullish/bearish engulfing

Run with:

```cmd
python -m unittest discover tests
```

## Integration test

`summarize_history()` was exercised end-to-end against an 80-bar synthetic candle series and
confirmed to return all 44 metric keys (old + new) with sane values, and `girp.api.main` was
re-imported after every change to confirm the FastAPI app still constructs cleanly. `/screen` and
`/rank` require no code changes to surface the new fields — they were already generic over
whatever `summarize_history()` returns.

## What this is not (yet)

- No dedicated technical-indicator API endpoint (`/assets/{symbol}/technicals`) — the values are
  only available through `/screen` and `/rank` result `metrics`, or by adding a formula/sort that
  references them. A standalone endpoint can be added later if the frontend needs to chart these
  without running a formula.
- Ichimoku's senkou spans are computed at their *current* values, not displaced forward 26 bars
  the way a charting library would draw the cloud. That displacement only matters for visual
  charts, which don't exist yet (see the pending "price chart" task).
- Supertrend/ADX/MFI have no configurable period in the API — they use the standard defaults
  (10/3, 14, 14). Making periods configurable per-request is a small follow-up if needed.
