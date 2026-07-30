from __future__ import annotations

from decimal import Decimal

ZERO = Decimal("0")
ONE = Decimal("1")


def dcf_fair_value(
    free_cash_flow: Decimal | None,
    shares_outstanding: Decimal | None,
    growth_rate: Decimal = Decimal("0.08"),
    discount_rate: Decimal = Decimal("0.10"),
    terminal_growth: Decimal = Decimal("0.025"),
    years: int = 5,
) -> Decimal | None:
    """Simple single-stage-growth-then-perpetuity DCF, per-share.

    Projects ``years`` of free cash flow growing at ``growth_rate``,
    discounts each year back at ``discount_rate``, adds a Gordon-growth
    terminal value using ``terminal_growth``, then divides by shares
    outstanding. This is intentionally a first-slice model -- no debt
    netting, no multi-stage growth fade, no scenario weighting.
    """
    if free_cash_flow is None or shares_outstanding in (None, ZERO):
        return None
    if free_cash_flow <= ZERO:
        return None
    if discount_rate <= terminal_growth:
        return None
    if years <= 0:
        return None

    present_value = ZERO
    projected = free_cash_flow
    discount_factor = ONE
    for _ in range(years):
        projected = projected * (ONE + growth_rate)
        discount_factor = discount_factor * (ONE + discount_rate)
        present_value += projected / discount_factor

    terminal_cash_flow = projected * (ONE + terminal_growth)
    terminal_value = terminal_cash_flow / (discount_rate - terminal_growth)
    present_value += terminal_value / discount_factor

    return present_value / shares_outstanding
