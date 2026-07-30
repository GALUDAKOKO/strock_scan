from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from girp.domain import Candle
from girp.formula import EvaluationError, evaluate_formula, parse_formula
from girp.services import MarketDataService
from girp.technical import summarize_history

TRADING_DAYS_PER_YEAR = Decimal("252")
DAYS_PER_YEAR = Decimal("365.25")


@dataclass(frozen=True)
class Trade:
    side: str
    symbol: str
    timestamp: str
    price: Decimal
    shares: Decimal
    cash: Decimal


@dataclass(frozen=True)
class BacktestResult:
    symbol: str
    formula: str
    initial_cash: Decimal
    final_equity: Decimal
    total_return_pct: Decimal
    max_drawdown_pct: Decimal
    trades: list[Trade]
    equity_curve: list[dict[str, Any]]
    cagr_pct: Decimal | None = None
    sharpe_ratio: Decimal | None = None
    win_rate_pct: Decimal | None = None
    profit_factor: Decimal | None = None
    win_count: int = 0
    loss_count: int = 0
    commission_pct: Decimal = Decimal("0")
    slippage_pct: Decimal = Decimal("0")
    error: str | None = None


class BacktestService:
    def __init__(self, market_data: MarketDataService) -> None:
        self.market_data = market_data

    def run(
        self,
        symbol: str,
        formula: str,
        start: date | None = None,
        end: date | None = None,
        interval: str = "1d",
        refresh: bool = False,
        initial_cash: Decimal = Decimal("100000"),
        commission_pct: Decimal = Decimal("0"),
        slippage_pct: Decimal = Decimal("0"),
    ) -> BacktestResult:
        if initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        if commission_pct < 0 or slippage_pct < 0:
            raise ValueError("commission_pct and slippage_pct must not be negative")

        parsed = parse_formula(formula)
        candles = self.market_data.get_history(
            symbol,
            start=start,
            end=end,
            interval=interval,
            refresh=refresh,
        )
        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        if not ordered:
            return _empty_result(symbol, formula, initial_cash, commission_pct, slippage_pct, "No price history available.")

        cash = initial_cash
        shares = Decimal("0")
        trades: list[Trade] = []
        equity_curve: list[dict[str, Any]] = []
        peak_equity = initial_cash
        max_drawdown_pct = Decimal("0")
        one = Decimal("1")

        for index, candle in enumerate(ordered, start=1):
            metrics = summarize_history(ordered[:index])
            signal = _safe_signal(parsed, metrics)

            if signal and shares == 0:
                buy_price = candle.close * (one + slippage_pct)
                cash_after_commission = cash * (one - commission_pct)
                shares = cash_after_commission / buy_price if buy_price > 0 else Decimal("0")
                cash = Decimal("0")
                trades.append(_trade("BUY", symbol, candle, buy_price, shares, cash))
            elif not signal and shares > 0:
                sell_price = candle.close * (one - slippage_pct)
                proceeds = shares * sell_price
                cash = proceeds * (one - commission_pct)
                trades.append(_trade("SELL", symbol, candle, sell_price, shares, cash))
                shares = Decimal("0")

            equity = cash + (shares * candle.close)
            if equity > peak_equity:
                peak_equity = equity
            drawdown_pct = ((peak_equity - equity) / peak_equity) * Decimal("100") if peak_equity else Decimal("0")
            if drawdown_pct > max_drawdown_pct:
                max_drawdown_pct = drawdown_pct

            equity_curve.append(
                {
                    "timestamp": candle.timestamp.isoformat(),
                    "close": candle.close,
                    "equity": equity,
                    "cash": cash,
                    "shares": shares,
                    "signal": signal,
                }
            )

        last_close = ordered[-1].close
        final_equity = cash + (shares * last_close)
        total_return_pct = ((final_equity - initial_cash) / initial_cash) * Decimal("100")

        cagr_pct = _cagr_pct(initial_cash, final_equity, ordered[0].timestamp, ordered[-1].timestamp)
        sharpe_ratio = _sharpe_ratio(equity_curve)
        win_rate_pct, profit_factor, win_count, loss_count = _round_trip_stats(trades)

        return BacktestResult(
            symbol=symbol.upper(),
            formula=formula,
            initial_cash=initial_cash,
            final_equity=final_equity,
            total_return_pct=total_return_pct,
            max_drawdown_pct=max_drawdown_pct,
            trades=trades,
            equity_curve=equity_curve,
            cagr_pct=cagr_pct,
            sharpe_ratio=sharpe_ratio,
            win_rate_pct=win_rate_pct,
            profit_factor=profit_factor,
            win_count=win_count,
            loss_count=loss_count,
            commission_pct=commission_pct,
            slippage_pct=slippage_pct,
        )


def _safe_signal(parsed: Any, metrics: dict[str, Any]) -> bool:
    try:
        return evaluate_formula(parsed, metrics)
    except EvaluationError:
        return False


def _trade(side: str, symbol: str, candle: Candle, price: Decimal, shares: Decimal, cash: Decimal) -> Trade:
    return Trade(
        side=side,
        symbol=symbol.upper(),
        timestamp=candle.timestamp.isoformat(),
        price=price,
        shares=shares,
        cash=cash,
    )


def _cagr_pct(initial_cash: Decimal, final_equity: Decimal, start_ts: Any, end_ts: Any) -> Decimal | None:
    if initial_cash <= 0 or final_equity <= 0:
        return None
    days = (end_ts - start_ts).days
    if days <= 0:
        return None
    years = Decimal(days) / DAYS_PER_YEAR
    if years <= 0:
        return None
    ratio = final_equity / initial_cash
    try:
        # ratio ** (1/years) via exp(ln(ratio) / years); Decimal has no fractional pow, so use float
        # for the exponent only, keeping the base computation in Decimal.
        growth = float(ratio) ** (1.0 / float(years))
    except (OverflowError, ValueError, ZeroDivisionError):
        return None
    return (Decimal(str(growth)) - Decimal("1")) * Decimal("100")


def _sharpe_ratio(equity_curve: list[dict[str, Any]], risk_free_rate: Decimal = Decimal("0")) -> Decimal | None:
    equities = [point["equity"] for point in equity_curve]
    if len(equities) < 3:
        return None

    returns: list[Decimal] = []
    for previous, current in zip(equities, equities[1:]):
        if previous == 0:
            continue
        returns.append((current - previous) / previous)

    if len(returns) < 2:
        return None

    mean_return = sum(returns) / Decimal(len(returns))
    variance = sum((r - mean_return) ** 2 for r in returns) / Decimal(len(returns))
    if variance == 0:
        return None
    std_dev = variance.sqrt()

    daily_excess = mean_return - (risk_free_rate / TRADING_DAYS_PER_YEAR)
    daily_sharpe = daily_excess / std_dev
    return daily_sharpe * TRADING_DAYS_PER_YEAR.sqrt()


def _round_trip_stats(trades: list[Trade]) -> tuple[Decimal | None, Decimal | None, int, int]:
    round_trips: list[Decimal] = []  # profit in currency per round trip
    pending_buy: Trade | None = None

    for trade in trades:
        if trade.side == "BUY":
            pending_buy = trade
        elif trade.side == "SELL" and pending_buy is not None:
            profit = (trade.price - pending_buy.price) * pending_buy.shares
            round_trips.append(profit)
            pending_buy = None

    if not round_trips:
        return None, None, 0, 0

    wins = [profit for profit in round_trips if profit > 0]
    losses = [profit for profit in round_trips if profit < 0]

    win_rate_pct = (Decimal(len(wins)) / Decimal(len(round_trips))) * Decimal("100")

    gross_profit = sum(wins) if wins else Decimal("0")
    gross_loss = abs(sum(losses)) if losses else Decimal("0")
    if gross_loss == 0:
        profit_factor = None if gross_profit == 0 else Decimal("999.99")
    else:
        profit_factor = gross_profit / gross_loss

    return win_rate_pct, profit_factor, len(wins), len(losses)


def _empty_result(
    symbol: str,
    formula: str,
    initial_cash: Decimal,
    commission_pct: Decimal,
    slippage_pct: Decimal,
    error: str,
) -> BacktestResult:
    return BacktestResult(
        symbol=symbol.upper(),
        formula=formula,
        initial_cash=initial_cash,
        final_equity=initial_cash,
        total_return_pct=Decimal("0"),
        max_drawdown_pct=Decimal("0"),
        trades=[],
        equity_curve=[],
        commission_pct=commission_pct,
        slippage_pct=slippage_pct,
        error=error,
    )
