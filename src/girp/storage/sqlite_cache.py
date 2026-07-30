from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from girp.domain import Asset, Candle, FinancialStatement, Watchlist


class SQLiteCache:
    def __init__(self, path: str | Path = "data/girp_cache.sqlite3") -> None:
        self.path = Path(path)
        if self.path != Path(":memory:"):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self.initialize()

    def initialize(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS assets (
                symbol TEXT PRIMARY KEY,
                market TEXT,
                name TEXT,
                asset_type TEXT NOT NULL,
                currency TEXT,
                sector TEXT,
                industry TEXT,
                country TEXT,
                exchange TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS candles (
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                open TEXT NOT NULL,
                high TEXT NOT NULL,
                low TEXT NOT NULL,
                close TEXT NOT NULL,
                adjusted_close TEXT,
                volume INTEGER NOT NULL,
                PRIMARY KEY (symbol, timestamp)
            );

            CREATE TABLE IF NOT EXISTS financial_statements (
                symbol TEXT NOT NULL,
                period TEXT NOT NULL,
                reported_at TEXT,
                metrics_json TEXT NOT NULL,
                PRIMARY KEY (symbol, period, reported_at)
            );

            CREATE INDEX IF NOT EXISTS idx_candles_symbol_timestamp
                ON candles(symbol, timestamp);

            CREATE TABLE IF NOT EXISTS watchlists (
                name TEXT PRIMARY KEY,
                symbols_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS symbol_updates (
                symbol TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ai_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                provider TEXT NOT NULL,
                api_key TEXT NOT NULL,
                model TEXT,
                updated_at TEXT NOT NULL
            );
            """
        )
        self._connection.commit()
        self._migrate_asset_classification_columns()

    def _migrate_asset_classification_columns(self) -> None:
        """Add sector/industry/country/exchange to `assets` if this is a pre-Phase-7 database.

        CREATE TABLE IF NOT EXISTS only applies to brand-new tables, so existing on-disk
        caches created before these columns existed need an explicit, idempotent ALTER TABLE.
        """
        existing_columns = {
            row["name"] for row in self._connection.execute("PRAGMA table_info(assets)").fetchall()
        }
        for column in ("sector", "industry", "country", "exchange"):
            if column not in existing_columns:
                self._connection.execute(f"ALTER TABLE assets ADD COLUMN {column} TEXT")
        self._connection.commit()

    def touch_symbol_update(self, symbol: str) -> datetime:
        """Record that fresh data for `symbol` was just pulled from the provider.

        Called whenever get_info/get_history/get_financials actually hits the
        provider (cache miss or explicit refresh), so callers can show the
        user when a stock's data was last refreshed from source.
        """
        updated_at = datetime.now(UTC)
        self._connection.execute(
            """
            INSERT INTO symbol_updates(symbol, updated_at)
            VALUES (?, ?)
            ON CONFLICT(symbol) DO UPDATE SET updated_at=excluded.updated_at
            """,
            (symbol.upper(), updated_at.isoformat()),
        )
        self._connection.commit()
        return updated_at

    def get_symbol_update(self, symbol: str) -> datetime | None:
        row = self._connection.execute(
            "SELECT updated_at FROM symbol_updates WHERE symbol = ?",
            (symbol.upper(),),
        ).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(row["updated_at"])

    def get_symbol_updates(self, symbols: list[str]) -> dict[str, datetime | None]:
        if not symbols:
            return {}
        upper_symbols = [symbol.upper() for symbol in symbols]
        placeholders = ",".join("?" for _ in upper_symbols)
        rows = self._connection.execute(
            f"SELECT symbol, updated_at FROM symbol_updates WHERE symbol IN ({placeholders})",
            upper_symbols,
        ).fetchall()
        found = {row["symbol"]: datetime.fromisoformat(row["updated_at"]) for row in rows}
        return {symbol: found.get(symbol) for symbol in upper_symbols}

    def upsert_asset(self, asset: Asset) -> None:
        self._connection.execute(
            """
            INSERT INTO assets(symbol, market, name, asset_type, currency, sector, industry, country, exchange, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                market=excluded.market,
                name=excluded.name,
                asset_type=excluded.asset_type,
                currency=excluded.currency,
                sector=excluded.sector,
                industry=excluded.industry,
                country=excluded.country,
                exchange=excluded.exchange,
                updated_at=excluded.updated_at
            """,
            (
                asset.symbol.upper(),
                asset.market,
                asset.name,
                asset.asset_type,
                asset.currency,
                asset.sector,
                asset.industry,
                asset.country,
                asset.exchange,
                datetime.now(UTC).isoformat(),
            ),
        )
        self._connection.commit()

    def get_asset(self, symbol: str) -> Asset | None:
        row = self._connection.execute(
            "SELECT * FROM assets WHERE symbol = ?",
            (symbol.upper(),),
        ).fetchone()
        if row is None:
            return None
        return Asset(
            symbol=row["symbol"],
            market=row["market"],
            name=row["name"],
            asset_type=row["asset_type"],
            currency=row["currency"],
            sector=row["sector"] if "sector" in row.keys() else None,
            industry=row["industry"] if "industry" in row.keys() else None,
            country=row["country"] if "country" in row.keys() else None,
            exchange=row["exchange"] if "exchange" in row.keys() else None,
        )

    def upsert_candles(self, candles: list[Candle]) -> None:
        self._connection.executemany(
            """
            INSERT INTO candles(
                symbol, timestamp, open, high, low, close, adjusted_close, volume
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, timestamp) DO UPDATE SET
                open=excluded.open,
                high=excluded.high,
                low=excluded.low,
                close=excluded.close,
                adjusted_close=excluded.adjusted_close,
                volume=excluded.volume
            """,
            [
                (
                    candle.symbol.upper(),
                    candle.timestamp.isoformat(),
                    str(candle.open),
                    str(candle.high),
                    str(candle.low),
                    str(candle.close),
                    str(candle.adjusted_close) if candle.adjusted_close is not None else None,
                    candle.volume,
                )
                for candle in candles
            ],
        )
        self._connection.commit()

    def get_candles(
        self,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
    ) -> list[Candle]:
        clauses = ["symbol = ?"]
        values: list[Any] = [symbol.upper()]
        if start is not None:
            clauses.append("timestamp >= ?")
            values.append(start.isoformat())
        if end is not None:
            clauses.append("timestamp <= ?")
            values.append(end.isoformat())
        rows = self._connection.execute(
            f"SELECT * FROM candles WHERE {' AND '.join(clauses)} ORDER BY timestamp",
            values,
        ).fetchall()
        return [
            Candle(
                symbol=row["symbol"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                open=Decimal(row["open"]),
                high=Decimal(row["high"]),
                low=Decimal(row["low"]),
                close=Decimal(row["close"]),
                adjusted_close=Decimal(row["adjusted_close"]) if row["adjusted_close"] else None,
                volume=row["volume"],
            )
            for row in rows
        ]

    def upsert_financials(self, statements: list[FinancialStatement]) -> None:
        self._connection.executemany(
            """
            INSERT INTO financial_statements(symbol, period, reported_at, metrics_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(symbol, period, reported_at) DO UPDATE SET
                metrics_json=excluded.metrics_json
            """,
            [
                (
                    statement.symbol.upper(),
                    statement.period,
                    statement.reported_at.isoformat() if statement.reported_at else "",
                    json.dumps(statement.metrics, sort_keys=True),
                )
                for statement in statements
            ],
        )
        self._connection.commit()

    def get_financials(self, symbol: str) -> list[FinancialStatement]:
        rows = self._connection.execute(
            """
            SELECT * FROM financial_statements
            WHERE symbol = ?
            ORDER BY period, reported_at
            """,
            (symbol.upper(),),
        ).fetchall()
        return [
            FinancialStatement(
                symbol=row["symbol"],
                period=row["period"],
                reported_at=date.fromisoformat(row["reported_at"]) if row["reported_at"] else None,
                metrics=json.loads(row["metrics_json"]),
            )
            for row in rows
        ]

    def upsert_watchlist(self, name: str, symbols: list[str]) -> Watchlist:
        normalized_name = name.strip()
        ordered_symbols = list(dict.fromkeys(symbol.upper().strip() for symbol in symbols if symbol.strip()))
        updated_at = datetime.now(UTC)
        self._connection.execute(
            """
            INSERT INTO watchlists(name, symbols_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                symbols_json=excluded.symbols_json,
                updated_at=excluded.updated_at
            """,
            (normalized_name, json.dumps(ordered_symbols), updated_at.isoformat()),
        )
        self._connection.commit()
        return Watchlist(name=normalized_name, symbols=tuple(ordered_symbols), updated_at=updated_at)

    def get_watchlist(self, name: str) -> Watchlist | None:
        row = self._connection.execute(
            "SELECT * FROM watchlists WHERE name = ?",
            (name.strip(),),
        ).fetchone()
        if row is None:
            return None
        return _watchlist_from_row(row)

    def list_watchlists(self) -> list[Watchlist]:
        rows = self._connection.execute(
            "SELECT * FROM watchlists ORDER BY name"
        ).fetchall()
        return [_watchlist_from_row(row) for row in rows]

    def delete_watchlist(self, name: str) -> bool:
        cursor = self._connection.execute(
            "DELETE FROM watchlists WHERE name = ?",
            (name.strip(),),
        )
        self._connection.commit()
        return cursor.rowcount > 0

    def save_ai_settings(self, provider: str, api_key: str, model: str | None = None) -> None:
        """Persist a single AI provider + API key (single row, id fixed at 1).

        This is a user-facing "save my key in the app" convenience on top of the
        env-var-based get_provider() -- saving here overrides env vars, so a user can
        paste a key into the UI without touching server environment configuration.
        """
        updated_at = datetime.now(UTC).isoformat()
        self._connection.execute(
            """
            INSERT INTO ai_settings(id, provider, api_key, model, updated_at)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                provider=excluded.provider,
                api_key=excluded.api_key,
                model=excluded.model,
                updated_at=excluded.updated_at
            """,
            (provider, api_key, model, updated_at),
        )
        self._connection.commit()

    def get_ai_settings(self) -> dict[str, Any] | None:
        row = self._connection.execute(
            "SELECT provider, api_key, model, updated_at FROM ai_settings WHERE id = 1"
        ).fetchone()
        if row is None:
            return None
        return {
            "provider": row["provider"],
            "api_key": row["api_key"],
            "model": row["model"],
            "updated_at": row["updated_at"],
        }

    def delete_ai_settings(self) -> bool:
        cursor = self._connection.execute("DELETE FROM ai_settings WHERE id = 1")
        self._connection.commit()
        return cursor.rowcount > 0

    def close(self) -> None:
        self._connection.close()


def _watchlist_from_row(row: sqlite3.Row) -> Watchlist:
    return Watchlist(
        name=row["name"],
        symbols=tuple(json.loads(row["symbols_json"])),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
