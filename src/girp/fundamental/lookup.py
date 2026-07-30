from __future__ import annotations

import math
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from girp.domain import FinancialStatement

# Common yfinance line-item labels differ across versions. Each canonical field
# maps to a list of aliases tried in order.
ALIASES: dict[str, tuple[str, ...]] = {
    "total_revenue": ("Total Revenue", "TotalRevenue", "Revenue"),
    "gross_profit": ("Gross Profit", "GrossProfit"),
    "net_income": ("Net Income", "NetIncome", "Net Income Common Stockholders"),
    "ebit": ("EBIT", "Operating Income", "OperatingIncome"),
    "sga_expense": (
        "Selling General And Administration",
        "Selling General Administrative",
        "SG&A",
    ),
    "depreciation": ("Depreciation", "Depreciation And Amortization", "Reconciled Depreciation"),
    "total_assets": ("Total Assets", "TotalAssets"),
    "total_current_assets": ("Total Current Assets", "Current Assets", "CurrentAssets"),
    "receivables": ("Net Receivables", "Receivables", "Accounts Receivable"),
    "total_current_liabilities": (
        "Total Current Liabilities",
        "Current Liabilities",
        "CurrentLiabilities",
    ),
    "total_liabilities": (
        "Total Liab",
        "Total Liabilities Net Minority Interest",
        "TotalLiabilitiesNetMinorityInterest",
    ),
    "long_term_debt": ("Long Term Debt", "LongTermDebt"),
    "total_debt": ("Total Debt", "TotalDebt"),
    "total_equity": (
        "Total Stockholder Equity",
        "Stockholders Equity",
        "Total Equity Gross Minority Interest",
        "StockholdersEquity",
    ),
    "retained_earnings": ("Retained Earnings", "RetainedEarnings"),
    "cash_and_equivalents": ("Cash And Cash Equivalents", "CashAndCashEquivalents", "Cash"),
    "operating_cash_flow": (
        "Operating Cash Flow",
        "Total Cash From Operating Activities",
        "Cash Flow From Continuing Operating Activities",
    ),
    "capital_expenditure": ("Capital Expenditure", "Capital Expenditures", "CapitalExpenditures"),
    "free_cash_flow": ("Free Cash Flow", "FreeCashFlow"),
    "diluted_shares": (
        "Diluted Average Shares",
        "DilutedAverageShares",
        "Diluted Shares Outstanding",
        "Ordinary Shares Number",
    ),
    "basic_shares": ("Basic Average Shares", "BasicAverageShares"),
    "diluted_eps": ("Diluted EPS", "DilutedEPS"),
    "cost_of_revenue": ("Cost Of Revenue", "CostOfRevenue", "Reconciled Cost Of Revenue"),
    "net_ppe": ("Net PPE", "Property Plant And Equipment Net", "PropertyPlantEquipmentNet"),
}


def field(metrics: dict[str, Any], name: str) -> Decimal | None:
    """Look up a canonical fundamental field by trying its known aliases."""
    aliases = ALIASES.get(name, (name,))
    for alias in aliases:
        if alias in metrics:
            value = _to_decimal(metrics[alias])
            if value is not None:
                return value
    return None


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value)
        except InvalidOperation:
            return None
    return None


def annual_statements(statements: list[FinancialStatement]) -> list[FinancialStatement]:
    annual = [statement for statement in statements if statement.period == "annual"]
    return sorted(annual, key=_sort_key, reverse=True)


def _sort_key(statement: FinancialStatement) -> date:
    return statement.reported_at or date.min
