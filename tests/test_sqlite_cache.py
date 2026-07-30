from datetime import date, datetime
from decimal import Decimal
import unittest

from girp.domain import Asset, Candle, FinancialStatement
from girp.storage import SQLiteCache


class SQLiteCacheTests(unittest.TestCase):
    def test_round_trips_asset_candle_and_financials(self) -> None:
        cache = SQLiteCache(":memory:")
        cache.upsert_asset(Asset(symbol="ABC", market="SET", name="ABC Corp"))
        cache.upsert_candles(
            [
                Candle(
                    symbol="ABC",
                    timestamp=datetime(2024, 1, 2),
                    open=Decimal("10"),
                    high=Decimal("11"),
                    low=Decimal("9"),
                    close=Decimal("10.5"),
                    adjusted_close=Decimal("10.4"),
                    volume=1000,
                )
            ]
        )
        cache.upsert_financials(
            [
                FinancialStatement(
                    symbol="ABC",
                    period="annual",
                    reported_at=date(2024, 1, 1),
                    metrics={"revenue": 100},
                )
            ]
        )

        self.assertEqual(cache.get_asset("abc").market, "SET")
        self.assertEqual(cache.get_candles("abc")[0].close, Decimal("10.5"))
        self.assertEqual(cache.get_financials("abc")[0].metrics["revenue"], 100)

    def test_round_trips_asset_classification_fields(self) -> None:
        cache = SQLiteCache(":memory:")
        cache.upsert_asset(
            Asset(
                symbol="ABC",
                market="NASDAQ",
                name="ABC Corp",
                sector="Technology",
                industry="Software - Infrastructure",
                country="United States",
                exchange="NASDAQ Global Select",
            )
        )

        asset = cache.get_asset("abc")
        self.assertEqual(asset.sector, "Technology")
        self.assertEqual(asset.industry, "Software - Infrastructure")
        self.assertEqual(asset.country, "United States")
        self.assertEqual(asset.exchange, "NASDAQ Global Select")

    def test_classification_fields_default_to_none(self) -> None:
        cache = SQLiteCache(":memory:")
        cache.upsert_asset(Asset(symbol="ABC"))

        asset = cache.get_asset("abc")
        self.assertIsNone(asset.sector)
        self.assertIsNone(asset.industry)
        self.assertIsNone(asset.country)
        self.assertIsNone(asset.exchange)

    def test_migration_adds_classification_columns_to_pre_phase7_db(self) -> None:
        # Simulate an on-disk cache created before sector/industry/country/exchange existed:
        # a bare assets table with only the original columns, no migration having run yet.
        cache = SQLiteCache(":memory:")
        cache._connection.executescript(
            """
            DROP TABLE assets;
            CREATE TABLE assets (
                symbol TEXT PRIMARY KEY,
                market TEXT,
                name TEXT,
                asset_type TEXT NOT NULL,
                currency TEXT,
                updated_at TEXT NOT NULL
            );
            """
        )
        cache._connection.commit()

        # Re-running initialize() (as __init__ does on every connection) must add the
        # missing columns without raising and without losing existing rows.
        cache._connection.execute(
            "INSERT INTO assets(symbol, market, name, asset_type, currency, updated_at) "
            "VALUES ('OLD', 'NYSE', 'Old Corp', 'equity', 'USD', '2024-01-01T00:00:00+00:00')"
        )
        cache._connection.commit()
        cache.initialize()

        asset = cache.get_asset("OLD")
        self.assertEqual(asset.market, "NYSE")
        self.assertIsNone(asset.sector)

    def test_symbol_update_tracking(self) -> None:
        cache = SQLiteCache(":memory:")

        self.assertIsNone(cache.get_symbol_update("abc"))

        touched = cache.touch_symbol_update("abc")
        self.assertEqual(cache.get_symbol_update("ABC"), touched)

        many = cache.get_symbol_updates(["abc", "xyz"])
        self.assertEqual(many["ABC"], touched)
        self.assertIsNone(many["XYZ"])


if __name__ == "__main__":
    unittest.main()
