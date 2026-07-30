from __future__ import annotations

from decimal import Decimal
from typing import Any

from girp.domain import FinancialStatement
from girp.fundamental.lookup import annual_statements, field

ZERO = Decimal("0")


def piotroski_f_score(statements: list[FinancialStatement]) -> int | None:
    """9-point Piotroski F-Score. Needs two annual periods; returns None
    when there isn't enough history to compare year-over-year deltas."""
    annual = annual_statements(statements)
    if len(annual) < 2:
        return None
    current, prior = annual[0].metrics, annual[1].metrics

    net_income = field(current, "net_income")
    total_assets = field(current, "total_assets")
    prior_total_assets = field(prior, "total_assets")
    cfo = field(current, "operating_cash_flow")
    prior_net_income = field(prior, "net_income")
    prior_cfo = field(prior, "operating_cash_flow")

    if None in (net_income, total_assets, prior_total_assets, prior_net_income):
        return None

    roa = _div(net_income, total_assets)
    prior_roa = _div(prior_net_income, prior_total_assets)
    if roa is None or prior_roa is None:
        return None

    score = 0
    score += _point(net_income > ZERO)
    score += _point(cfo is not None and cfo > ZERO)
    score += _point(roa > prior_roa)
    score += _point(cfo is not None and cfo > net_income)

    current_lt_debt = field(current, "long_term_debt") or field(current, "total_debt")
    prior_lt_debt = field(prior, "long_term_debt") or field(prior, "total_debt")
    leverage_now = _div(current_lt_debt, total_assets)
    leverage_prior = _div(prior_lt_debt, prior_total_assets)
    if leverage_now is not None and leverage_prior is not None:
        score += _point(leverage_now <= leverage_prior)

    current_ratio_now = _div(field(current, "total_current_assets"), field(current, "total_current_liabilities"))
    current_ratio_prior = _div(field(prior, "total_current_assets"), field(prior, "total_current_liabilities"))
    if current_ratio_now is not None and current_ratio_prior is not None:
        score += _point(current_ratio_now >= current_ratio_prior)

    shares_now = field(current, "diluted_shares") or field(current, "basic_shares")
    shares_prior = field(prior, "diluted_shares") or field(prior, "basic_shares")
    if shares_now is not None and shares_prior is not None:
        score += _point(shares_now <= shares_prior)

    revenue_now = field(current, "total_revenue")
    revenue_prior = field(prior, "total_revenue")
    gross_now = _div(field(current, "gross_profit"), revenue_now) if revenue_now else None
    gross_prior = _div(field(prior, "gross_profit"), revenue_prior) if revenue_prior else None
    if gross_now is not None and gross_prior is not None:
        score += _point(gross_now >= gross_prior)

    turnover_now = _div(revenue_now, total_assets)
    turnover_prior = _div(revenue_prior, prior_total_assets)
    if turnover_now is not None and turnover_prior is not None:
        score += _point(turnover_now >= turnover_prior)

    return score


def altman_z_score(statements: list[FinancialStatement], market_cap: Decimal | None = None) -> Decimal | None:
    """Classic 5-factor Altman Z-Score for public manufacturing firms."""
    annual = annual_statements(statements)
    if not annual:
        return None
    latest = annual[0].metrics

    total_assets = field(latest, "total_assets")
    if total_assets in (None, ZERO):
        return None

    current_assets = field(latest, "total_current_assets")
    current_liabilities = field(latest, "total_current_liabilities")
    retained_earnings = field(latest, "retained_earnings")
    ebit = field(latest, "ebit")
    total_liabilities = field(latest, "total_liabilities")
    revenue = field(latest, "total_revenue")

    if None in (current_assets, current_liabilities, retained_earnings, ebit, total_liabilities, revenue):
        return None
    if total_liabilities == ZERO or market_cap is None:
        return None

    working_capital_ratio = (current_assets - current_liabilities) / total_assets
    retained_earnings_ratio = retained_earnings / total_assets
    ebit_ratio = ebit / total_assets
    equity_to_liabilities = market_cap / total_liabilities
    asset_turnover = revenue / total_assets

    return (
        (Decimal("1.2") * working_capital_ratio)
        + (Decimal("1.4") * retained_earnings_ratio)
        + (Decimal("3.3") * ebit_ratio)
        + (Decimal("0.6") * equity_to_liabilities)
        + (Decimal("1.0") * asset_turnover)
    )


def beneish_m_score(statements: list[FinancialStatement]) -> Decimal | None:
    """8-variable Beneish M-Score. Needs two annual periods with receivables,
    gross margin, PP&E, SG&A, and cash-flow line items populated. Returns
    None whenever any required input is missing, which is common with sparse
    provider data -- treat the result as a best-effort signal, not a fact."""
    annual = annual_statements(statements)
    if len(annual) < 2:
        return None
    current, prior = annual[0].metrics, annual[1].metrics

    revenue = field(current, "total_revenue")
    prior_revenue = field(prior, "total_revenue")
    receivables = field(current, "receivables")
    prior_receivables = field(prior, "receivables")
    gross_profit = field(current, "gross_profit")
    prior_gross_profit = field(prior, "gross_profit")
    total_assets = field(current, "total_assets")
    prior_total_assets = field(prior, "total_assets")
    current_assets = field(current, "total_current_assets")
    prior_current_assets = field(prior, "total_current_assets")
    net_ppe = field(current, "net_ppe")
    prior_net_ppe = field(prior, "net_ppe")
    depreciation = field(current, "depreciation")
    prior_depreciation = field(prior, "depreciation")
    sga = field(current, "sga_expense")
    prior_sga = field(prior, "sga_expense")
    current_liabilities = field(current, "total_current_liabilities")
    prior_current_liabilities = field(prior, "total_current_liabilities")
    total_debt = field(current, "total_debt") or field(current, "long_term_debt")
    prior_total_debt = field(prior, "total_debt") or field(prior, "long_term_debt")
    net_income = field(current, "net_income")
    cfo = field(current, "operating_cash_flow")

    required = [
        revenue,
        prior_revenue,
        receivables,
        prior_receivables,
        gross_profit,
        prior_gross_profit,
        total_assets,
        prior_total_assets,
        current_assets,
        prior_current_assets,
        net_ppe,
        prior_net_ppe,
        depreciation,
        prior_depreciation,
        sga,
        prior_sga,
        current_liabilities,
        prior_current_liabilities,
        total_debt,
        prior_total_debt,
        net_income,
        cfo,
    ]
    if any(value is None for value in required) or revenue == ZERO or prior_revenue == ZERO:
        return None
    if total_assets == ZERO or prior_total_assets == ZERO:
        return None

    dsri = _div(receivables / revenue, prior_receivables / prior_revenue)
    gmi = _div(prior_gross_profit / prior_revenue, gross_profit / revenue)
    aqi = _div(
        Decimal("1") - ((current_assets + net_ppe) / total_assets),
        Decimal("1") - ((prior_current_assets + prior_net_ppe) / prior_total_assets),
    )
    sgi = _div(revenue, prior_revenue)
    depi = _div(
        prior_depreciation / (prior_depreciation + prior_net_ppe),
        depreciation / (depreciation + net_ppe),
    )
    sgai = _div(sga / revenue, prior_sga / prior_revenue)
    lvgi = _div(
        (current_liabilities + total_debt) / total_assets,
        (prior_current_liabilities + prior_total_debt) / prior_total_assets,
    )
    tata = _div(net_income - cfo, total_assets)

    if None in (dsri, gmi, aqi, sgi, depi, sgai, lvgi, tata):
        return None

    return (
        Decimal("-4.84")
        + (Decimal("0.92") * dsri)
        + (Decimal("0.528") * gmi)
        + (Decimal("0.404") * aqi)
        + (Decimal("0.892") * sgi)
        + (Decimal("0.115") * depi)
        - (Decimal("0.172") * sgai)
        + (Decimal("4.679") * tata)
        - (Decimal("0.327") * lvgi)
    )


def _div(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator in (None, ZERO):
        return None
    return numerator / denominator


def _point(condition: bool) -> int:
    return 1 if condition else 0
