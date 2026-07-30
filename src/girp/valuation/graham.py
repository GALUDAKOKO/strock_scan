from __future__ import annotations

from decimal import Decimal

ZERO = Decimal("0")


def graham_number(eps: Decimal | None, book_value_per_share: Decimal | None) -> Decimal | None:
    """Benjamin Graham's defensive-investor fair value estimate:

        sqrt(22.5 * EPS * Book Value Per Share)

    Undefined (None) when EPS or book value is non-positive, since the
    formula assumes a profitable, solvent company.
    """
    if eps is None or book_value_per_share is None:
        return None
    if eps <= ZERO or book_value_per_share <= ZERO:
        return None
    return (Decimal("22.5") * eps * book_value_per_share).sqrt()


def margin_of_safety(fair_value: Decimal | None, price: Decimal | None) -> Decimal | None:
    """Percentage discount of price below fair value. Positive means the
    asset trades below estimated fair value (a margin of safety); negative
    means it trades above it."""
    if fair_value is None or price is None or fair_value == ZERO:
        return None
    return ((fair_value - price) / fair_value) * Decimal("100")
