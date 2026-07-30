# GIRP Phase 4

Phase 4 adds a first backtesting workflow using the same Formula DSL as screening and ranking.

## Scope

- Long-only formula backtest
- Buy when formula is true
- Sell when formula becomes false
- Uses rolling indicators only from data available up to each candle
- Tracks trades, equity curve, total return, and max drawdown
- `POST /backtest` API endpoint

## Example

```cmd
curl -X POST http://127.0.0.1:8000/backtest ^
  -H "Content-Type: application/json" ^
  -d "{\"symbol\":\"AAPL\",\"formula\":\"close > sma_20 AND close > ema_20\",\"start\":\"2026-01-01\",\"end\":\"2026-07-20\",\"initial_cash\":100000,\"refresh\":false}"
```

## Swagger body

```json
{
  "symbol": "AAPL",
  "formula": "close > sma_20 AND close > ema_20",
  "start": "2026-01-01",
  "end": "2026-07-20",
  "interval": "1d",
  "initial_cash": 100000,
  "refresh": false
}
```

## Notes

This is a first simulation slice, not a full brokerage model. It does not yet include fees, slippage, position sizing rules, dividends, or multi-asset portfolio allocation.