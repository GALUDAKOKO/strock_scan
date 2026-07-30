from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from girp.formula.parser import Comparison, Formula, parse_formula


class EvaluationError(ValueError):
    pass


def evaluate_formula(source: str | Formula, metrics: dict[str, Any]) -> bool:
    formula = parse_formula(source) if isinstance(source, str) else source
    result = evaluate_comparison(formula.first, metrics)

    for joiner, comparison in formula.rest:
        current = evaluate_comparison(comparison, metrics)
        if joiner == "AND":
            result = result and current
        elif joiner == "OR":
            result = result or current
        else:
            raise EvaluationError(f"Unsupported joiner: {joiner}")

    return result


def evaluate_comparison(comparison: Comparison, metrics: dict[str, Any]) -> bool:
    left = _resolve(comparison.left, metrics)
    right = _resolve(comparison.right, metrics)

    if left is None or right is None:
        return False

    if comparison.operator == "=":
        return left == right
    if comparison.operator == "!=":
        return left != right

    left_number = _as_decimal(left)
    right_number = _as_decimal(right)
    if left_number is None or right_number is None:
        return False

    if comparison.operator == ">":
        return left_number > right_number
    if comparison.operator == ">=":
        return left_number >= right_number
    if comparison.operator == "<":
        return left_number < right_number
    if comparison.operator == "<=":
        return left_number <= right_number

    raise EvaluationError(f"Unsupported operator: {comparison.operator}")


def _resolve(value: Any, metrics: dict[str, Any]) -> Any:
    if isinstance(value, str) and value in metrics:
        return metrics[value]
    return value


def _as_decimal(value: Any) -> Decimal | None:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value)
        except InvalidOperation:
            return None
    return None