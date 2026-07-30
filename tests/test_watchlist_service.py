import unittest

from girp.storage import SQLiteCache
from girp.watchlist import WatchlistService, parse_symbols


class ParseSymbolsTests(unittest.TestCase):
    def test_splits_on_commas_whitespace_and_newlines(self) -> None:
        raw = "aapl, msft\nptt.bk cpall.bk;  googl"
        self.assertEqual(parse_symbols(raw), ["AAPL", "MSFT", "PTT.BK", "CPALL.BK", "GOOGL"])

    def test_dedupes_while_preserving_order(self) -> None:
        self.assertEqual(parse_symbols("AAPL aapl AAPL msft"), ["AAPL", "MSFT"])

    def test_empty_string_yields_empty_list(self) -> None:
        self.assertEqual(parse_symbols("   \n  "), [])


class WatchlistServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cache = SQLiteCache(":memory:")
        self.service = WatchlistService(self.cache)

    def test_saves_and_retrieves_a_watchlist(self) -> None:
        self.service.save("SET50", "ptt.bk, cpall.bk, aot.bk")

        watchlist = self.service.get("SET50")

        self.assertIsNotNone(watchlist)
        self.assertEqual(watchlist.symbols, ("PTT.BK", "CPALL.BK", "AOT.BK"))
        self.assertIsNotNone(watchlist.updated_at)

    def test_save_accepts_a_symbol_list_too(self) -> None:
        self.service.save("Mag7", ["aapl", "msft", "aapl"])

        watchlist = self.service.get("Mag7")

        self.assertEqual(watchlist.symbols, ("AAPL", "MSFT"))

    def test_rejects_empty_name_or_symbols(self) -> None:
        with self.assertRaises(ValueError):
            self.service.save("", "AAPL")
        with self.assertRaises(ValueError):
            self.service.save("Empty", "   ")

    def test_lists_all_watchlists_sorted_by_name(self) -> None:
        self.service.save("Zeta", "AAPL")
        self.service.save("Alpha", "MSFT")

        names = [watchlist.name for watchlist in self.service.list_all()]

        self.assertEqual(names, ["Alpha", "Zeta"])

    def test_overwrites_existing_watchlist_on_save(self) -> None:
        self.service.save("Portfolio", "AAPL, MSFT")
        self.service.save("Portfolio", "GOOGL")

        watchlist = self.service.get("Portfolio")

        self.assertEqual(watchlist.symbols, ("GOOGL",))

    def test_deletes_a_watchlist(self) -> None:
        self.service.save("Temp", "AAPL")

        deleted = self.service.delete("Temp")

        self.assertTrue(deleted)
        self.assertIsNone(self.service.get("Temp"))

    def test_delete_returns_false_when_missing(self) -> None:
        self.assertFalse(self.service.delete("DoesNotExist"))

    def test_get_returns_none_when_missing(self) -> None:
        self.assertIsNone(self.service.get("Nope"))


if __name__ == "__main__":
    unittest.main()
