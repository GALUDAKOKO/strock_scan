# GIRP Phase 1

Phase 1 creates the runnable foundation for GIRP without committing the project to a narrow product workflow too early.

## Scope

- Core Python package under `src/girp`
- Domain models for assets, markets, OHLCV candles, financial statements, and provider metadata
- Provider interface matching `spec/provider_interface.md`
- SQLite cache for normalized price history and financial payloads
- Optional yfinance-backed provider implementation
- Market data service that coordinates provider + cache refresh behavior
- Formula DSL parser for basic comparisons joined by `AND` / `OR`
- FastAPI app exposing health, history, financials, info, and formula parsing endpoints
- Unit tests for formula parsing, SQLite cache behavior, and service/cache integration

## Non-goals

- React frontend
- Full screening/ranking/backtest workflow
- Complete indicator and fundamental plugin libraries
- Production authentication
- Deployment automation

## Run

Install dependencies:

```cmd
py -m pip install -r requirements.txt
```

Start API from cmd:

```cmd
set PYTHONPATH=src
py -m uvicorn girp.api.main:app --reload
```

Or use the helper:

```cmd
run_api.cmd
```

Run tests:

```cmd
set PYTHONPATH=src
py -m unittest discover -s tests
```

Alternatively install the project in editable mode once:

```cmd
py -m pip install -e .
py -m uvicorn girp.api.main:app --reload
```

## Notes

The yfinance provider is optional at import time. Tests use in-memory fakes so the core architecture can be validated without network access.