# GIRP Phase 3

Phase 3 adds ranking on top of market data, indicators, and screening formulas.

## Scope

- Additional ranking metrics:
  - `close_vs_sma_20`
  - `close_vs_ema_20`
  - `momentum_score`
- Ranking service for multiple symbols
- Optional formula filter before ranking
- Sort direction and result limit
- `POST /rank` API endpoint

## Example

```cmd
curl -X POST http://127.0.0.1:8000/rank ^
  -H "Content-Type: application/json" ^
  -d "{\"symbols\":[\"AAPL\",\"PTT.BK\",\"CPALL.BK\"],\"sort_by\":\"momentum_score\",\"formula\":\"close > sma_20\",\"start\":\"2026-01-01\",\"end\":\"2026-07-20\",\"refresh\":true}"
```

## Useful sort_by values

```text
momentum_score
close_vs_sma_20
close_vs_ema_20
rsi_14
volume
close
```