from __future__ import annotations

import re

from girp.domain import Watchlist
from girp.storage import SQLiteCache

# Splits on commas, whitespace, and newlines so pasted CSV columns, one-per-line
# lists, and space-separated tickers all parse the same way.
_SPLIT_RE = re.compile(r"[\s,;]+")


def parse_symbols(raw: str) -> list[str]:
    """Parse free-form pasted/CSV text into a deduplicated, uppercased symbol list."""
    tokens = [token.strip().upper() for token in _SPLIT_RE.split(raw) if token.strip()]
    return list(dict.fromkeys(tokens))


class WatchlistService:
    """Named lists of symbols so users don't have to retype a universe every
    time they screen, rank, or backtest. Not a live "all stocks in a market"
    feed -- there is no such API on the yfinance provider -- just persistent,
    user-curated (or CSV-imported) symbol lists."""

    def __init__(self, cache: SQLiteCache) -> None:
        self.cache = cache

    def list_all(self) -> list[Watchlist]:
        return self.cache.list_watchlists()

    def get(self, name: str) -> Watchlist | None:
        return self.cache.get_watchlist(name)

    def save(self, name: str, symbols: list[str] | str) -> Watchlist:
        if not name or not name.strip():
            raise ValueError("Watchlist name is required.")
        symbol_list = parse_symbols(symbols) if isinstance(symbols, str) else [s.upper() for s in symbols]
        if not symbol_list:
            raise ValueError("Watchlist must contain at least one symbol.")
        return self.cache.upsert_watchlist(name, symbol_list)

    def delete(self, name: str) -> bool:
        return self.cache.delete_watchlist(name)
