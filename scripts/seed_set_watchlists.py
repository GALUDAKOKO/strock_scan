"""One-off seed script: saves SET50 and SET100 as watchlists in the local
SQLite cache (data/girp_cache.sqlite3), so they're immediately available in
the Screener/Ranking "load from watchlist" picker.

Source: official SET50/SET100 constituent list for July 1 - December 31,
2026 (H2 2026 cycle), published by the Stock Exchange of Thailand, updated
2026-06-17: https://www.set.or.th/en/market/information/securities-list/constituents-list-set50-set100

SET indices are reviewed every six months. Re-run this script (or just edit
the watchlist from the Watchlists page) after the next rebalance to keep it
current.

Usage (from the project root, with PYTHONPATH=src):
    set PYTHONPATH=src
    py scripts/seed_set_watchlists.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from girp.storage import SQLiteCache  # noqa: E402
from girp.watchlist import WatchlistService  # noqa: E402

SET50 = """
ADVANC AOT AWC BANPU BBL BCP BDMS BEM BH BJC CCET COM7 CPALL CPF CPN CRC
DELTA EGCO GPSC GULF HMPRO IVL KBANK KKP KTB KTC LH MINT MRDIYT MTC OR OSP
PTT PTTEP PTTGC RATCH SCB SCC SCGP TCAP TFG THAI TIDLOR TISCO TLI TOP TRUE
TTB TU WHA
""".split()

SET100 = """
AAV ADVANC AEONTS AMATA AOT AP AURA AWC BA BAM BANPU BBL BCH BCP BCPG BDMS
BEM BGRIM BH BJC BLA BTG BTS CBG CCET CENTEL CHG CK COM7 CPALL CPF CPN CRC
DELTA DOHOME EA EGCO ERW GFPT GLOBAL GPSC GULF GUNKUL HANA HMPRO ICHI IRPC
IVL JMT JTS KBANK KCE KKP KTB KTC LH M MEGA MINT MOSHI MRDIYT MTC OR OSP
PLANB PR9 PRM PTG PTT PTTEP PTTGC QH RATCH RCL SAWAD SCB SCC SCGP SIRI
SPALI SPRC STA STECON STGT TASCO TCAP TFG THAI THCOM TIDLOR TISCO TLI TOA
TOP TRUE TTB TU VGI WHA WHAUP
""".split()


def to_yfinance_symbols(tickers: list[str]) -> list[str]:
    return [f"{ticker}.BK" for ticker in tickers]


def main() -> None:
    cache = SQLiteCache(Path("data/girp_cache.sqlite3"))
    service = WatchlistService(cache)

    set50 = service.save("SET50", to_yfinance_symbols(SET50))
    print(f"Saved '{set50.name}' with {len(set50.symbols)} symbols.")
    assert len(set50.symbols) == 50, f"expected 50 symbols, got {len(set50.symbols)}"

    set100 = service.save("SET100", to_yfinance_symbols(SET100))
    print(f"Saved '{set100.name}' with {len(set100.symbols)} symbols.")
    assert len(set100.symbols) == 100, f"expected 100 symbols, got {len(set100.symbols)}"


if __name__ == "__main__":
    main()
