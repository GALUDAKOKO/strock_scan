from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from girp.domain import FinancialStatement
from girp.fundamental.lookup import annual_statements, field

ZERO = Decimal("0")


def compute_fundamentals(
    statements: list[FinancialStatement],
    price: Decimal | None = None,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive fundamental metrics from financial statements, price, and an
    optional provider snapshot (e.g. shares outstanding, trailing PE).

    Every value is best-effort: missing inputs yield ``None`` for the
    dependent metric rather than raising, so this can be merged directly into
    the same metrics dict used by the Formula DSL / screening / ranking
    engines.
    """
    snapshot = snapshot or {}
    annual = annual_statements(statements)
    latest = annual[0].metrics if annual else {}
    previous = annual[1].metrics if len(annual) > 1 else {}

    revenue = field(latest, "total_revenue")
    prev_revenue = field(previous, "total_revenue")
    net_income = field(latest, "net_income")
    total_assets = field(latest, "total_assets")
    total_equity = field(latest, "total_equity")
    total_liabilities = field(latest, "total_liabilities")
    prev_total_assets = field(previous, "total_assets")

    operating_cash_flow = field(latest, "operating_cash_flow")
    capex = field(latest, "capital_expenditure")
    free_cash_flow = field(latest, "free_cash_flow")
    if free_cash_flow is None and operating_cash_flow is not None and capex is not None:
        free_cash_flow = operating_cash_flow - abs(capex)

    shares_outstanding = _decimal(snapshot.get("shares_outstanding"))
    if shares_outstanding is None:
        shares_outstanding = field(latest, "diluted_shares") or field(latest, "basic_shares")

    eps = field(latest, "diluted_eps")
    if eps is None and net_income is not None and shares_outstanding not in (None, ZERO):
        eps = net_income / shares_outstanding
    if eps is None:
        eps = _decimal(snapshot.get("trailing_eps"))

    book_value_per_share = None
    if total_equity is not None and shares_outstanding not in (None, ZERO):
        book_value_per_share = total_equity / shares_outstanding
    if book_value_per_share is None:
        book_value_per_share = _decimal(snapshot.get("book_value"))

    resolved_price = price if price is not None else _decimal(snapshot.get("price"))

    pe = _safe_div(resolved_price, eps)
    if pe is None:
        pe = _decimal(snapshot.get("trailing_pe"))

    pbv = _safe_div(resolved_price, book_value_per_share)
    if pbv is None:
        pbv = _decimal(snapshot.get("price_to_book"))

    roe = _safe_div(net_income, total_equity)
    if roe is None:
        roe = _decimal(snapshot.get("return_on_equity"))

    roa = _safe_div(net_income, total_assets)
    if roa is None:
        roa = _decimal(snapshot.get("return_on_assets"))

    invested_capital = None
    if total_equity is not None:
        total_debt = field(latest, "total_debt") or field(latest, "long_term_debt")
        invested_capital = total_equity + (total_debt or ZERO)
    roic = _safe_div(net_income, invested_capital)

    net_margin = _safe_div(net_income, revenue)
    if net_margin is None:
        net_margin = _decimal(snapshot.get("profit_margins"))

    revenue_growth = _safe_div(
        (revenue - prev_revenue) if revenue is not None and prev_revenue is not None else None,
        prev_revenue,
    )
    if revenue_growth is None:
        revenue_growth = _decimal(snapshot.get("revenue_growth"))

    current_assets = field(latest, "total_current_assets")
    current_liabilities = field(latest, "total_current_liabilities")
    current_ratio = _safe_div(current_assets, current_liabilities)

    debt_to_equity = _safe_div(field(latest, "total_debt") or field(latest, "long_term_debt"), total_equity)
    if debt_to_equity is None:
        debt_to_equity = _decimal(snapshot.get("debt_to_equity"))

    asset_growth = _safe_div(
        (total_assets - prev_total_assets) if total_assets is not None and prev_total_assets is not None else None,
        prev_total_assets,
    )

    owner_earnings = None
    if net_income is not None:
        depreciation = field(latest, "depreciation") or ZERO
        maint_capex = abs(capex) if capex is not None else ZERO
        owner_earnings = net_income + depreciation - maint_capex

    market_cap = _decimal(snapshot.get("market_cap"))
    if market_cap is None and resolved_price is not None and shares_outstanding is not None:
        market_cap = resolved_price * shares_outstanding

    return {
        "revenue": revenue,
        "net_income": net_income,
        "total_assets": total_assets,
        "total_equity": total_equity,
        "total_liabilities": total_liabilities,
        "shares_outstanding": shares_outstanding,
        "eps": eps,
        "book_value_per_share": book_value_per_share,
        "price": resolved_price,
        "pe": pe,
        "pbv": pbv,
        "roe": roe,
        "roa": roa,
        "roic": roic,
        "net_margin": net_margin,
        "revenue_growth": revenue_growth,
        "asset_growth": asset_growth,
        "current_ratio": current_ratio,
        "debt_to_equity": debt_to_equity,
        "free_cash_flow": free_cash_flow,
        "owner_earnings": owner_earnings,
        "market_cap": market_cap,
        "dividend_yield": _decimal(snapshot.get("dividend_yield")),
        "beta": _decimal(snapshot.get("beta")),
    }


def _safe_div(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator in (None, ZERO):
        return None
    return numerator / denominator


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
