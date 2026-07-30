from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re


OPERATORS = {"=", "!=", ">", ">=", "<", "<="}
JOINERS = {"AND", "OR"}
TOKEN_RE = re.compile(r'"[^"]*"|>=|<=|!=|=|>|<|\(|\)|[A-Za-z_][A-Za-z0-9_.]*|-?\d+(?:\.\d+)?')


class ParseError(ValueError):
    pass


@dataclass(frozen=True)
class Comparison:
    left: str
    operator: str
    right: str | Decimal


@dataclass(frozen=True)
class Formula:
    first: Comparison
    rest: tuple[tuple[str, Comparison], ...] = ()


def parse_formula(source: str) -> Formula:
    tokens = TOKEN_RE.findall(source)
    if not tokens:
        raise ParseError("Formula is empty.")

    parser = _Parser(tokens)
    formula = parser.parse_expression()
    if parser.has_more:
        raise ParseError(f"Unexpected token: {parser.peek()}")
    return formula


class _Parser:
    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.index = 0

    @property
    def has_more(self) -> bool:
        return self.index < len(self.tokens)

    def peek(self) -> str:
        return self.tokens[self.index]

    def take(self) -> str:
        token = self.tokens[self.index]
        self.index += 1
        return token

    def parse_expression(self) -> Formula:
        first = self.parse_condition()
        rest: list[tuple[str, Comparison]] = []
        while self.has_more and self.peek().upper() in JOINERS:
            joiner = self.take().upper()
            rest.append((joiner, self.parse_condition()))
        return Formula(first=first, rest=tuple(rest))

    def parse_condition(self) -> Comparison:
        left = self._take_identifier("Expected metric name.")
        if not self.has_more:
            raise ParseError("Expected comparison operator.")
        operator = self.take()
        if operator not in OPERATORS:
            raise ParseError(f"Unsupported operator: {operator}")
        if not self.has_more:
            raise ParseError("Expected comparison value.")
        right = self._parse_value(self.take())
        return Comparison(left=left, operator=operator, right=right)

    def _take_identifier(self, message: str) -> str:
        if not self.has_more:
            raise ParseError(message)
        token = self.take()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", token):
            raise ParseError(message)
        return token

    def _parse_value(self, token: str) -> str | Decimal:
        if token.startswith('"') and token.endswith('"'):
            return token[1:-1]
        try:
            return Decimal(token)
        except InvalidOperation:
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", token):
                return token
            raise ParseError(f"Unsupported value: {token}") from None
