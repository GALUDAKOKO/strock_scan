from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from girp.fundamental import compute_fundamentals
from girp.services import MarketDataService
from girp.valuation.dcf import dcf_fair_value
from girp.valuation.graham import graham_number, margin_of_safety


@dataclass(frozen=True)
class ValuationResult:
    symbol: str
    price: Decimal | None
    eps: Decimal | None
    book_value_per_share: Decimal | None
    free_cash_flow: Decimal | None
    shares_outstanding: Decimal | None
    graham_number: Decimal | None
    graham_margin_of_safety_pct: Decimal | None
    dcf_fair_value: Decimal | None
    dcf_margin_of_safety_pct: Decimal | None
    fundamentals: dict[str, Any]
    error: str | None = None


class ValuationService:
    def __init__(self, market_data: MarketDataService) -> None:
        self.market_data = market_data

    def valuate(
        self,
        symbol: str,
        growth_rate: Decimal = Decimal("0.08"),
        discount_rate: Decimal = Decimal("0.10"),
        terminal_growth: Decimal = Decimal("0.025"),
        years: int = 5,
        refresh: bool = False,
    ) -> ValuationResult:
        try:
            statements = self.market_data.get_financials(symbol, refresh=refresh)
            snapshot = self.market_data.get_snapshot(symbol)
            price = _latest_price(self.market_data, symbol, refresh=refresh)

            fundamentals = compute_fundamentals(statements, price=price, snapshot=snapshot)

            graham = graham_number(fundamentals.get("eps"), fundamentals.get("book_value_per_share"))
            graham_mos = margin_of_safety(graham, fundamentals.get("price"))

            dcf_value = dcf_fair_value(
                fundamentals.get("free_cash_flow"),
                fundamentals.get("shares_outstanding"),
                growth_rate=growth_rate,
                discount_rate=discount_rate,
                terminal_growth=terminal_growth,
                years=years,
            )
            dcf_mos = margin_of_safety(dcf_value, fundamentals.get("price"))

            return ValuationResult(
                symbol=symbol.upper(),
                price=fundamentals.get("price"),
                eps=fundamentals.get("eps"),
                book_value_per_share=fundamentals.get("book_value_per_share"),
                free_cash_flow=fundamentals.get("free_cash_flow"),
                shares_outstanding=fundamentals.get("shares_outstanding"),
                graham_number=graham,
                graham_margin_of_safety_pct=graham_mos,
                dcf_fair_value=dcf_value,
                dcf_margin_of_safety_pct=dcf_mos,
                fundamentals=fundamentals,
            )
        except (RuntimeError, ValueError) as exc:
            return ValuationResult(
                symbol=symbol.upper(),
                price=None,
                eps=None,
                book_value_per_share=None,
                free_cash_flow=None,
                shares_outstanding=None,
                graham_number=None,
                graham_margin_of_safety_pct=None,
                dcf_fair_value=None,
                dcf_margin_of_safety_pct=None,
                fundamentals={},
                error=str(exc),
            )


def _latest_price(market_data: MarketDataService, symbol: str, refresh: bool) -> Decimal | None:
    candles = market_data.get_history(symbol, refresh=refresh)
    if not candles:
        return None
    latest = max(candles, key=lambda candle: candle.timestamp)
    return latest.close
