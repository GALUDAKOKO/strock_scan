# GIRP Phase 5

Phase 5 adds fundamental analysis and valuation on top of Phase 1-4 market data, screening, ranking, and backtesting.

## Scope

- Fundamental metric engine (`src/girp/fundamental`):
  - Extracts revenue, net income, assets, equity, liabilities, EPS, book value per share from `FinancialStatement` payloads (income statement + balance sheet + cash flow, merged per period)
  - Derives PE, PBV, ROE, ROA, ROIC, net margin, revenue growth, asset growth, current ratio, debt-to-equity, free cash flow, owner earnings, market cap
  - Falls back to a provider quote snapshot (price, trailing PE/EPS, book value, ROE/ROA, margins) when statement data is missing
  - Piotroski F-Score (9-point), Altman Z-Score, Beneish M-Score — all best-effort, returning `None` when required inputs are unavailable rather than guessing
- Valuation engine (`src/girp/valuation`):
  - Graham Number (`sqrt(22.5 * EPS * Book Value Per Share)`) and margin of safety vs. current price
  - Single-stage-growth-then-perpetuity DCF fair value per share, with configurable growth rate, discount rate, terminal growth, and projection years
  - `ValuationService` wiring statements + price + snapshot into both models
- `yfinance` provider now merges income statement, balance sheet, and cash flow per period, and exposes a best-effort `get_snapshot()` (price, market cap, shares outstanding, trailing ratios) — not part of the strict provider protocol, so other providers can omit it
- `GET /assets/{symbol}/fundamentals` — fundamentals + Piotroski/Altman/Beneish scores
- `POST /valuation` — Graham number, DCF fair value, margins of safety
- `ScreeningService.screen(...)` and `RankingService.rank(...)` accept an optional `include_fundamentals=True` flag to merge fundamental metrics into the same metrics dict used by the Formula DSL, so screens/ranks can filter or sort on `pe`, `roe`, `revenue_growth`, etc. Default is `False` to keep existing technical-only behavior unchanged.

## Example

```cmd
curl http://127.0.0.1:8000/assets/AAPL/fundamentals

curl -X POST http://127.0.0.1:8000/valuation ^
  -H "Content-Type: application/json" ^
  -d "{\"symbol\":\"AAPL\",\"growth_rate\":0.08,\"discount_rate\":0.10,\"terminal_growth\":0.025,\"years\":5}"

curl -X POST http://127.0.0.1:8000/screen ^
  -H "Content-Type: application/json" ^
  -d "{\"symbols\":[\"AAPL\",\"MSFT\"],\"formula\":\"pe < 30 AND roe > 0.15\",\"include_fundamentals\":true}"
```

## Notes

Fundamental line items are only as reliable as the underlying `yfinance` payloads, which vary by ticker, market, and filing lag. Every derived metric and score degrades to `None` rather than raising when an input is missing — treat scores like Beneish M as directional signals, not verified facts. This is a first fundamental/valuation slice: no multi-stage DCF, no sector-relative scoring, no analyst estimate blending.
