# GIRP Phase 2

Phase 2 adds the first usable screening workflow on top of Phase 1 market data.

## Scope

- Technical summary from price history:
  - `close`
  - `volume`
  - `sma_20`
  - `ema_20`
  - `rsi_14`
- Formula evaluator for parsed DSL expressions
- Metric-to-number and metric-to-metric comparisons
- Screening service for multiple symbols
- `POST /screen` API endpoint

## Example

```cmd
curl -X POST http://127.0.0.1:8000/screen ^
  -H "Content-Type: application/json" ^
  -d "{\"symbols\":[\"AAPL\",\"PTT.BK\"],\"formula\":\"close > sma_20 AND rsi_14 < 70\",\"start\":\"2024-01-01\",\"end\":\"2024-03-01\",\"refresh\":true}"
```

## Formula Examples

```text
close > sma_20
close > sma_20 AND rsi_14 < 70
volume > 1000000 OR close >= ema_20
```

## Notes

This is intentionally a first screening slice. Future phases can add fundamental metrics, ranking buckets, backtest execution, and frontend workflows without changing the Phase 2 contract.