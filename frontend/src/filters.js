// Checkbox filter presets. Each maps to one Formula DSL comparison. Selected
// filters are AND-joined into the final formula sent to /screen and /rank.

export const TECHNICAL_FILTERS = [
  { id: 'close_above_sma20', label: 'Close > SMA 20', expr: 'close > sma_20' },
  { id: 'close_above_ema20', label: 'Close > EMA 20', expr: 'close > ema_20' },
  { id: 'close_below_sma20', label: 'Close < SMA 20', expr: 'close < sma_20' },
  { id: 'rsi_oversold', label: 'RSI 14 < 30 (oversold)', expr: 'rsi_14 < 30' },
  { id: 'rsi_overbought', label: 'RSI 14 > 70 (overbought)', expr: 'rsi_14 > 70' },
  { id: 'momentum_positive', label: 'Momentum score > 0', expr: 'momentum_score > 0' },
  { id: 'macd_bullish', label: 'MACD > Signal (bullish)', expr: 'macd > macd_signal' },
  { id: 'macd_bearish', label: 'MACD < Signal (bearish)', expr: 'macd < macd_signal' },
  { id: 'adx_strong_trend', label: 'ADX 14 > 25 (strong trend)', expr: 'adx_14 > 25' },
  { id: 'plus_di_above_minus_di', label: '+DI > -DI (uptrend bias)', expr: 'plus_di_14 > minus_di_14' },
  { id: 'bollinger_breakout_up', label: 'Close > Bollinger upper', expr: 'close > bollinger_upper_20' },
  { id: 'bollinger_breakout_down', label: 'Close < Bollinger lower', expr: 'close < bollinger_lower_20' },
  { id: 'cci_oversold', label: 'CCI 20 < -100 (oversold)', expr: 'cci_20 < -100' },
  { id: 'cci_overbought', label: 'CCI 20 > 100 (overbought)', expr: 'cci_20 > 100' },
  { id: 'mfi_oversold', label: 'MFI 14 < 20 (oversold)', expr: 'mfi_14 < 20' },
  { id: 'mfi_overbought', label: 'MFI 14 > 80 (overbought)', expr: 'mfi_14 > 80' },
  { id: 'supertrend_up', label: 'Supertrend direction up', expr: 'supertrend_direction > 0' },
  { id: 'supertrend_down', label: 'Supertrend direction down', expr: 'supertrend_direction < 0' },
  { id: 'close_above_resistance', label: 'Close > 20-bar resistance', expr: 'close > resistance_20' },
  { id: 'close_below_support', label: 'Close < 20-bar support', expr: 'close < support_20' },
  { id: 'bullish_engulfing', label: 'Bullish engulfing candle', expr: 'pattern_bullish_engulfing > 0' },
  { id: 'bearish_engulfing', label: 'Bearish engulfing candle', expr: 'pattern_bearish_engulfing > 0' },
]

export const FUNDAMENTAL_FILTERS = [
  { id: 'pe_under_15', label: 'PE < 15', expr: 'pe < 15' },
  { id: 'pe_under_25', label: 'PE < 25', expr: 'pe < 25' },
  { id: 'pbv_under_3', label: 'PBV < 3', expr: 'pbv < 3' },
  { id: 'roe_above_10', label: 'ROE > 10%', expr: 'roe > 0.10' },
  { id: 'roe_above_15', label: 'ROE > 15%', expr: 'roe > 0.15' },
  { id: 'roa_positive', label: 'ROA > 0', expr: 'roa > 0' },
  { id: 'revenue_growth_positive', label: 'Revenue growth > 0', expr: 'revenue_growth > 0' },
  { id: 'debt_to_equity_under_1', label: 'Debt/Equity < 1', expr: 'debt_to_equity < 1' },
  { id: 'current_ratio_above_1', label: 'Current ratio > 1', expr: 'current_ratio > 1' },
]

// Sector uses Yahoo Finance's own taxonomy (what yfinance's `sector` field actually
// returns), not strict GICS wording, so the checkbox values match real data 1:1.
export const SECTORS = [
  'Technology',
  'Healthcare',
  'Financial Services',
  'Consumer Cyclical',
  'Consumer Defensive',
  'Industrials',
  'Energy',
  'Utilities',
  'Real Estate',
  'Basic Materials',
  'Communication Services',
]

// yfinance's quoteType values, lowercased (matches Asset.asset_type in the backend).
export const ASSET_TYPES = ['equity', 'etf', 'index', 'mutualfund', 'currency', 'cryptocurrency', 'future']

export function buildFormula(selectedExprs, customFormula) {
  const parts = [...selectedExprs]
  if (customFormula && customFormula.trim()) {
    parts.push(customFormula.trim())
  }
  return parts.join(' AND ')
}
