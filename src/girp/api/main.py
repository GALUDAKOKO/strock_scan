from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from girp.ai import PROVIDER_CLASSES, AIProviderNotConfigured, AIService, LazyProvider
from girp.backtesting import BacktestService
from girp.domain import Asset, Candle, FinancialStatement
from girp.formula import ParseError, parse_formula
from girp.fundamental import altman_z_score, beneish_m_score, compute_fundamentals, piotroski_f_score
from girp.providers.yfinance_provider import YFinanceProvider
from girp.ranking import RankingService
from girp.screening import ScreeningService
from girp.services import MarketDataService
from girp.storage import SQLiteCache
from girp.technical import summarize_history
from girp.valuation import ValuationService
from girp.watchlist import WatchlistService


app = FastAPI(title="GIRP API", version="0.5.0")

# The React frontend (frontend/) runs on a separate dev-server origin (Vite's
# default localhost:5173) and calls this API directly from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_service() -> MarketDataService:
    cache = SQLiteCache(Path("data/girp_cache.sqlite3"))
    return MarketDataService(provider=YFinanceProvider(), cache=cache)


def get_watchlist_service() -> WatchlistService:
    return WatchlistService(SQLiteCache(Path("data/girp_cache.sqlite3")))


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "GIRP API",
        "version": "0.5.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "asset_info": "/assets/{symbol}",
            "history": "/assets/{symbol}/history",
            "technicals": "/assets/{symbol}/technicals",
            "financials": "/assets/{symbol}/financials",
            "fundamentals": "/assets/{symbol}/fundamentals",
            "formula_parse": "/formula/parse",
            "screen": "/screen",
            "rank": "/rank",
            "backtest": "/backtest",
            "valuation": "/valuation",
            "watchlists": "/watchlists",
            "ai_explain_formula": "/ai/explain-formula",
            "ai_debug_formula": "/ai/debug-formula",
            "ai_summarize": "/ai/summarize",
            "ai_compare": "/ai/compare",
            "ai_suggest_strategy": "/ai/suggest-strategy",
            "ai_optimize_strategy": "/ai/optimize-strategy",
            "ai_settings": "/ai/settings",
        },
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/assets/{symbol}")
def asset_info(symbol: str, refresh: bool = False) -> dict[str, Any]:
    service = get_service()
    try:
        asset = service.get_info(symbol, refresh=refresh)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _asset_to_dict(asset, updated_at=service.get_last_updated(symbol))


@app.get("/assets/{symbol}/history")
def history(
    symbol: str,
    start: date | None = None,
    end: date | None = None,
    interval: str = Query("1d", pattern=r"^\d+[a-zA-Z]+$"),
    refresh: bool = False,
) -> list[dict[str, Any]]:
    try:
        candles = get_service().get_history(
            symbol,
            start=start,
            end=end,
            interval=interval,
            refresh=refresh,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return [_candle_to_dict(candle) for candle in candles]


@app.get("/assets/{symbol}/technicals")
def technicals(
    symbol: str,
    start: date | None = None,
    end: date | None = None,
    interval: str = Query("1d", pattern=r"^\d+[a-zA-Z]+$"),
    refresh: bool = False,
) -> dict[str, Any]:
    service = get_service()
    try:
        candles = service.get_history(symbol, start=start, end=end, interval=interval, refresh=refresh)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    metrics = summarize_history(candles)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"No price history available for '{symbol}'.")

    return {
        "symbol": symbol.upper(),
        "metrics": {key: _number(value) for key, value in metrics.items() if key not in ("symbol", "timestamp")},
        "timestamp": metrics.get("timestamp"),
        "updated_at": _datetime_or_none(service.get_last_updated(symbol)),
    }


@app.get("/assets/{symbol}/financials")
def financials(symbol: str, refresh: bool = False) -> list[dict[str, Any]]:
    try:
        statements = get_service().get_financials(symbol, refresh=refresh)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return [_statement_to_dict(statement) for statement in statements]


@app.get("/assets/{symbol}/fundamentals")
def fundamentals(symbol: str, refresh: bool = False) -> dict[str, Any]:
    service = get_service()
    try:
        statements = service.get_financials(symbol, refresh=refresh)
        history = service.get_history(symbol, refresh=refresh)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    price = max(history, key=lambda candle: candle.timestamp).close if history else None
    snapshot = service.get_snapshot(symbol)
    metrics = compute_fundamentals(statements, price=price, snapshot=snapshot)

    return {
        "symbol": symbol.upper(),
        "metrics": {key: _number(value) for key, value in metrics.items()},
        "piotroski_f_score": piotroski_f_score(statements),
        "altman_z_score": _number(altman_z_score(statements, market_cap=metrics.get("market_cap"))),
        "beneish_m_score": _number(beneish_m_score(statements)),
        "updated_at": _datetime_or_none(service.get_last_updated(symbol)),
    }


@app.post("/formula/parse")
def formula_parse(payload: dict[str, str]) -> dict[str, Any]:
    source = payload.get("formula", "")
    try:
        formula = parse_formula(source)
    except ParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "first": _comparison_to_dict(formula.first),
        "rest": [
            {"joiner": joiner, "condition": _comparison_to_dict(condition)}
            for joiner, condition in formula.rest
        ],
    }


@app.post("/screen")
def screen(payload: dict[str, Any]) -> dict[str, Any]:
    symbols = payload.get("symbols", [])
    formula = payload.get("formula", "")
    if not isinstance(symbols, list) or not all(isinstance(symbol, str) for symbol in symbols):
        raise HTTPException(status_code=400, detail="symbols must be a list of strings")
    if not formula:
        raise HTTPException(status_code=400, detail="formula is required")

    service = get_service()
    try:
        results = ScreeningService(service).screen(
            symbols=symbols,
            formula=formula,
            start=_date_or_none(payload.get("start")),
            end=_date_or_none(payload.get("end")),
            interval=payload.get("interval", "1d"),
            refresh=bool(payload.get("refresh", False)),
            include_fundamentals=bool(payload.get("include_fundamentals", False)),
        )
    except ParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    updated_at_by_symbol = service.get_last_updated_many([result.symbol for result in results])
    return {
        "formula": formula,
        "count": len(results),
        "passed": sum(1 for result in results if result.passed),
        "results": [
            _screening_result_to_dict(result, updated_at=updated_at_by_symbol.get(result.symbol.upper()))
            for result in results
        ],
    }


@app.post("/rank")
def rank(payload: dict[str, Any]) -> dict[str, Any]:
    symbols = payload.get("symbols", [])
    if not isinstance(symbols, list) or not all(isinstance(symbol, str) for symbol in symbols):
        raise HTTPException(status_code=400, detail="symbols must be a list of strings")

    service = get_service()
    try:
        results = RankingService(service).rank(
            symbols=symbols,
            sort_by=payload.get("sort_by", "momentum_score"),
            descending=bool(payload.get("descending", True)),
            formula=payload.get("formula"),
            start=_date_or_none(payload.get("start")),
            end=_date_or_none(payload.get("end")),
            interval=payload.get("interval", "1d"),
            refresh=bool(payload.get("refresh", False)),
            limit=_int_or_none(payload.get("limit")),
            include_fundamentals=bool(payload.get("include_fundamentals", False)),
        )
    except ParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    ranked = [result for result in results if result.rank is not None]
    updated_at_by_symbol = service.get_last_updated_many([result.symbol for result in results])
    return {
        "sort_by": payload.get("sort_by", "momentum_score"),
        "descending": bool(payload.get("descending", True)),
        "formula": payload.get("formula"),
        "count": len(results),
        "ranked": len(ranked),
        "results": [
            _ranking_result_to_dict(result, updated_at=updated_at_by_symbol.get(result.symbol.upper()))
            for result in results
        ],
    }


@app.post("/backtest")
def backtest(payload: dict[str, Any]) -> dict[str, Any]:
    symbol = payload.get("symbol", "")
    formula = payload.get("formula", "")
    if not isinstance(symbol, str) or not symbol:
        raise HTTPException(status_code=400, detail="symbol is required")
    if not isinstance(formula, str) or not formula:
        raise HTTPException(status_code=400, detail="formula is required")

    service = get_service()
    try:
        result = BacktestService(service).run(
            symbol=symbol,
            formula=formula,
            start=_date_or_none(payload.get("start")),
            end=_date_or_none(payload.get("end")),
            interval=payload.get("interval", "1d"),
            refresh=bool(payload.get("refresh", False)),
            initial_cash=_decimal_or_default(payload.get("initial_cash"), Decimal("100000")),
            commission_pct=_decimal_or_default(payload.get("commission_pct"), Decimal("0")),
            slippage_pct=_decimal_or_default(payload.get("slippage_pct"), Decimal("0")),
        )
    except ParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return _backtest_result_to_dict(result, updated_at=service.get_last_updated(result.symbol))


@app.post("/valuation")
def valuation(payload: dict[str, Any]) -> dict[str, Any]:
    symbol = payload.get("symbol", "")
    if not isinstance(symbol, str) or not symbol:
        raise HTTPException(status_code=400, detail="symbol is required")

    service = get_service()
    result = ValuationService(service).valuate(
        symbol=symbol,
        growth_rate=_decimal_or_default(payload.get("growth_rate"), Decimal("0.08")),
        discount_rate=_decimal_or_default(payload.get("discount_rate"), Decimal("0.10")),
        terminal_growth=_decimal_or_default(payload.get("terminal_growth"), Decimal("0.025")),
        years=_int_or_none(payload.get("years")) or 5,
        refresh=bool(payload.get("refresh", False)),
    )
    return _valuation_result_to_dict(result, updated_at=service.get_last_updated(result.symbol))


@app.get("/watchlists")
def list_watchlists() -> dict[str, Any]:
    watchlists = get_watchlist_service().list_all()
    return {"watchlists": [_watchlist_to_dict(watchlist) for watchlist in watchlists]}


@app.get("/watchlists/{name}")
def get_watchlist(name: str) -> dict[str, Any]:
    watchlist = get_watchlist_service().get(name)
    if watchlist is None:
        raise HTTPException(status_code=404, detail=f"Watchlist '{name}' not found.")
    return _watchlist_to_dict(watchlist)


@app.put("/watchlists/{name}")
def save_watchlist(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    symbols = payload.get("symbols", [])
    is_string = isinstance(symbols, str)
    is_string_list = isinstance(symbols, list) and all(isinstance(symbol, str) for symbol in symbols)
    if not is_string and not is_string_list:
        raise HTTPException(status_code=400, detail="symbols must be a string or a list of strings")

    try:
        watchlist = get_watchlist_service().save(name, symbols)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _watchlist_to_dict(watchlist)


@app.delete("/watchlists/{name}")
def delete_watchlist(name: str) -> dict[str, Any]:
    deleted = get_watchlist_service().delete(name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Watchlist '{name}' not found.")
    return {"name": name, "deleted": True}


def _ai_settings_cache() -> SQLiteCache:
    return SQLiteCache(Path("data/girp_cache.sqlite3"))


def get_ai_service() -> AIService:
    """Build an AIService, preferring a provider+key saved via the /ai/settings UI.

    Falls back to the env-var-based get_provider() (ANTHROPIC_API_KEY / OPENAI_API_KEY /
    GEMINI_API_KEY) when nothing has been saved through the UI, and to UnconfiguredProvider
    when neither is set.
    """
    settings = _ai_settings_cache().get_ai_settings()
    if settings is not None:
        provider = LazyProvider(settings["provider"], settings["api_key"], settings.get("model"))
        return AIService(provider=provider)
    return AIService()


@app.post("/ai/explain-formula")
def ai_explain_formula(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("formula", "")
    lang = payload.get("lang", "en")
    if not isinstance(source, str) or not source:
        raise HTTPException(status_code=400, detail="formula is required")
    try:
        explanation = get_ai_service().explain_formula(source, lang=lang)
    except ParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"formula": source, "explanation": explanation}


@app.post("/ai/debug-formula")
def ai_debug_formula(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("formula", "")
    lang = payload.get("lang", "en")
    if not isinstance(source, str) or not source:
        raise HTTPException(status_code=400, detail="formula is required")
    result = get_ai_service().debug_formula(source, lang=lang)
    return {
        "formula": source,
        "is_valid": result.is_valid,
        "message": result.message,
        "suggestions": list(result.suggestions),
    }


@app.post("/ai/summarize")
def ai_summarize(payload: dict[str, Any]) -> dict[str, Any]:
    symbol = payload.get("symbol", "")
    metrics = payload.get("metrics", {})
    lang = payload.get("lang", "en")
    if not isinstance(symbol, str) or not symbol:
        raise HTTPException(status_code=400, detail="symbol is required")
    if not isinstance(metrics, dict):
        raise HTTPException(status_code=400, detail="metrics must be an object")
    try:
        summary = get_ai_service().summarize(symbol, metrics, lang=lang)
    except AIProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"symbol": symbol, "summary": summary}


@app.post("/ai/compare")
def ai_compare(payload: dict[str, Any]) -> dict[str, Any]:
    symbols = payload.get("symbols", [])
    metrics_by_symbol = payload.get("metrics_by_symbol", {})
    lang = payload.get("lang", "en")
    if not isinstance(symbols, list) or not all(isinstance(symbol, str) for symbol in symbols):
        raise HTTPException(status_code=400, detail="symbols must be a list of strings")
    if not isinstance(metrics_by_symbol, dict):
        raise HTTPException(status_code=400, detail="metrics_by_symbol must be an object")
    try:
        comparison = get_ai_service().compare(symbols, metrics_by_symbol, lang=lang)
    except AIProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"symbols": symbols, "comparison": comparison}


@app.post("/ai/suggest-strategy")
def ai_suggest_strategy(payload: dict[str, Any]) -> dict[str, Any]:
    goal = payload.get("goal", "")
    lang = payload.get("lang", "en")
    if not isinstance(goal, str) or not goal:
        raise HTTPException(status_code=400, detail="goal is required")
    try:
        suggestion = get_ai_service().suggest_strategy(goal, lang=lang)
    except AIProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"goal": goal, "suggestion": suggestion}


@app.post("/ai/optimize-strategy")
def ai_optimize_strategy(payload: dict[str, Any]) -> dict[str, Any]:
    formula = payload.get("formula", "")
    backtest_metrics = payload.get("backtest_metrics", {})
    lang = payload.get("lang", "en")
    if not isinstance(formula, str) or not formula:
        raise HTTPException(status_code=400, detail="formula is required")
    if not isinstance(backtest_metrics, dict):
        raise HTTPException(status_code=400, detail="backtest_metrics must be an object")
    try:
        suggestion = get_ai_service().optimize_strategy(formula, backtest_metrics, lang=lang)
    except AIProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"formula": formula, "suggestion": suggestion}


def _mask_api_key(api_key: str) -> str:
    if len(api_key) <= 4:
        return "*" * len(api_key)
    return f"{'*' * (len(api_key) - 4)}{api_key[-4:]}"


@app.get("/ai/settings")
def ai_get_settings() -> dict[str, Any]:
    settings = _ai_settings_cache().get_ai_settings()
    if settings is None:
        env_provider = (
            "anthropic"
            if os.environ.get("ANTHROPIC_API_KEY")
            else "openai"
            if os.environ.get("OPENAI_API_KEY")
            else "gemini"
            if os.environ.get("GEMINI_API_KEY")
            else None
        )
        return {"configured": env_provider is not None, "source": "env" if env_provider else None, "provider": env_provider, "api_key_masked": None, "model": None}
    return {
        "configured": True,
        "source": "saved",
        "provider": settings["provider"],
        "api_key_masked": _mask_api_key(settings["api_key"]),
        "model": settings.get("model"),
        "updated_at": settings.get("updated_at"),
    }


@app.post("/ai/settings")
def ai_save_settings(payload: dict[str, Any]) -> dict[str, Any]:
    provider = payload.get("provider", "")
    api_key = payload.get("api_key", "")
    model = payload.get("model") or None
    if provider not in PROVIDER_CLASSES:
        raise HTTPException(
            status_code=400,
            detail=f"provider must be one of: {', '.join(sorted(PROVIDER_CLASSES))}",
        )
    if not isinstance(api_key, str) or not api_key.strip():
        raise HTTPException(status_code=400, detail="api_key is required")

    # Saving does not require the provider's SDK package to be installed yet -- the key is
    # only actually used (and the SDK only actually imported) the first time an LLM-backed
    # endpoint is called, via LazyProvider. This lets a user paste a key in now and install
    # the SDK later without the save itself failing.
    _ai_settings_cache().save_ai_settings(provider, api_key.strip(), model)
    return {"saved": True, "provider": provider, "api_key_masked": _mask_api_key(api_key.strip())}


@app.delete("/ai/settings")
def ai_delete_settings() -> dict[str, Any]:
    deleted = _ai_settings_cache().delete_ai_settings()
    return {"deleted": deleted}


def _watchlist_to_dict(watchlist: Any) -> dict[str, Any]:
    return {
        "name": watchlist.name,
        "symbols": list(watchlist.symbols),
        "count": len(watchlist.symbols),
        "updated_at": watchlist.updated_at.isoformat() if watchlist.updated_at else None,
    }


def _valuation_result_to_dict(result: Any, updated_at: Any = None) -> dict[str, Any]:
    return {
        "symbol": result.symbol,
        "price": _number(result.price),
        "eps": _number(result.eps),
        "book_value_per_share": _number(result.book_value_per_share),
        "free_cash_flow": _number(result.free_cash_flow),
        "shares_outstanding": _number(result.shares_outstanding),
        "graham_number": _number(result.graham_number),
        "graham_margin_of_safety_pct": _number(result.graham_margin_of_safety_pct),
        "dcf_fair_value": _number(result.dcf_fair_value),
        "dcf_margin_of_safety_pct": _number(result.dcf_margin_of_safety_pct),
        "fundamentals": {key: _number(value) for key, value in result.fundamentals.items()},
        "error": result.error,
        "updated_at": _datetime_or_none(updated_at),
    }


def _decimal_or_default(value: Any, default: Decimal) -> Decimal:
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="decimal values must be numeric") from exc


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="limit must be an integer") from exc
    if number <= 0:
        raise HTTPException(status_code=400, detail="limit must be positive")
    return number


def _date_or_none(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise HTTPException(status_code=400, detail="date values must use YYYY-MM-DD")


def _backtest_result_to_dict(result: Any, updated_at: Any = None) -> dict[str, Any]:
    return {
        "symbol": result.symbol,
        "formula": result.formula,
        "initial_cash": _number(result.initial_cash),
        "final_equity": _number(result.final_equity),
        "total_return_pct": _number(result.total_return_pct),
        "max_drawdown_pct": _number(result.max_drawdown_pct),
        "cagr_pct": _number(result.cagr_pct),
        "sharpe_ratio": _number(result.sharpe_ratio),
        "win_rate_pct": _number(result.win_rate_pct),
        "profit_factor": _number(result.profit_factor),
        "win_count": result.win_count,
        "loss_count": result.loss_count,
        "commission_pct": _number(result.commission_pct),
        "slippage_pct": _number(result.slippage_pct),
        "trade_count": len(result.trades),
        "trades": [_trade_to_dict(trade) for trade in result.trades],
        "equity_curve": [
            {key: _number(value) for key, value in point.items()}
            for point in result.equity_curve
        ],
        "error": result.error,
        "updated_at": _datetime_or_none(updated_at),
    }


def _trade_to_dict(trade: Any) -> dict[str, Any]:
    return {
        "side": trade.side,
        "symbol": trade.symbol,
        "timestamp": trade.timestamp,
        "price": _number(trade.price),
        "shares": _number(trade.shares),
        "cash": _number(trade.cash),
    }


def _ranking_result_to_dict(result: Any, updated_at: Any = None) -> dict[str, Any]:
    return {
        "rank": result.rank,
        "symbol": result.symbol,
        "score": _number(result.score),
        "passed_filter": result.passed_filter,
        "metrics": {key: _number(value) for key, value in result.metrics.items()},
        "error": result.error,
        "updated_at": _datetime_or_none(updated_at),
    }


def _screening_result_to_dict(result: Any, updated_at: Any = None) -> dict[str, Any]:
    return {
        "symbol": result.symbol,
        "passed": result.passed,
        "metrics": {key: _number(value) for key, value in result.metrics.items()},
        "error": result.error,
        "updated_at": _datetime_or_none(updated_at),
    }


def _asset_to_dict(asset: Asset, updated_at: Any = None) -> dict[str, Any]:
    return {
        "symbol": asset.symbol,
        "market": asset.market,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "currency": asset.currency,
        "sector": asset.sector,
        "industry": asset.industry,
        "country": asset.country,
        "exchange": asset.exchange,
        "updated_at": _datetime_or_none(updated_at),
    }


def _candle_to_dict(candle: Candle) -> dict[str, Any]:
    return {
        "symbol": candle.symbol,
        "timestamp": candle.timestamp.isoformat(),
        "open": _number(candle.open),
        "high": _number(candle.high),
        "low": _number(candle.low),
        "close": _number(candle.close),
        "adjusted_close": _number(candle.adjusted_close),
        "volume": candle.volume,
    }


def _statement_to_dict(statement: FinancialStatement) -> dict[str, Any]:
    return {
        "symbol": statement.symbol,
        "period": statement.period,
        "reported_at": statement.reported_at.isoformat() if statement.reported_at else None,
        "metrics": statement.metrics,
    }


def _comparison_to_dict(comparison: Any) -> dict[str, Any]:
    return {
        "left": comparison.left,
        "operator": comparison.operator,
        "right": _number(comparison.right),
    }


def _number(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def _datetime_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat()