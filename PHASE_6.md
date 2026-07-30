# GIRP Phase 6

Phase 6 adds saved watchlists so screening, ranking, and backtesting don't require retyping a symbol list every time.

## Scope

- `watchlists` table in the SQLite cache: `name` (primary key), `symbols_json`, `updated_at`
- `WatchlistService` (`src/girp/watchlist`): save (create or overwrite), get, list, delete. Accepts either a symbol list or free-form pasted/CSV text (`parse_symbols` splits on commas, whitespace, semicolons, and newlines), dedupes, and uppercases
- API:
  - `GET /watchlists` — list all watchlists with symbol counts
  - `GET /watchlists/{name}` — fetch one
  - `PUT /watchlists/{name}` — create or replace, body `{"symbols": [...] }` or `{"symbols": "AAPL, MSFT\nGOOGL"}`
  - `DELETE /watchlists/{name}`
- Frontend: a Watchlists page to create/edit/delete named lists (paste or import a `.csv`/`.txt` file), plus a "load from watchlist" picker on the Screener and Ranking pages that fills the symbols box in one click

## What this is not

There is still no "load every stock in a market" button. `yfinance` has no exchange-wide symbol directory API, so watchlists are the substitute: paste in an index's official constituent list (SET50, S&P 500, NASDAQ 100, your own portfolio, etc.) once, save it, and reuse it. No lists ship pre-seeded, since index constituents change over time and a stale hardcoded list would be worse than none.

## Example

```cmd
curl -X PUT http://127.0.0.1:8000/watchlists/SET50 ^
  -H "Content-Type: application/json" ^
  -d "{\"symbols\":\"PTT.BK, CPALL.BK, AOT.BK, ADVANC.BK\"}"

curl http://127.0.0.1:8000/watchlists

curl http://127.0.0.1:8000/watchlists/SET50
```
