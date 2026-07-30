import { useState } from 'react'
import { useLanguage } from '../i18n/LanguageContext.jsx'

// Every field the Formula DSL can reference in /screen, /rank, and /backtest.
// Grouped for readability; each row can be copied straight into a formula.
const GROUPS = [
  {
    key: 'price',
    fields: [
      { field: 'close', example: 'close > 100' },
      { field: 'volume', example: 'volume > 1000000' },
    ],
  },
  {
    key: 'trend',
    fields: [
      { field: 'sma_20', example: 'close > sma_20' },
      { field: 'ema_20', example: 'close > ema_20' },
      { field: 'close_vs_sma_20', example: 'close_vs_sma_20 > 5' },
      { field: 'close_vs_ema_20', example: 'close_vs_ema_20 > 5' },
      { field: 'momentum_score', example: 'momentum_score > 0' },
    ],
  },
  {
    key: 'oscillators',
    fields: [
      { field: 'rsi_14', example: 'rsi_14 < 30' },
      { field: 'macd', example: 'macd > macd_signal' },
      { field: 'macd_signal', example: 'macd > macd_signal' },
      { field: 'macd_histogram', example: 'macd_histogram > 0' },
      { field: 'cci_20', example: 'cci_20 < -100' },
    ],
  },
  {
    key: 'volatility',
    fields: [
      { field: 'atr_14', example: 'atr_14 < 5' },
      { field: 'bollinger_upper_20', example: 'close > bollinger_upper_20' },
      { field: 'bollinger_lower_20', example: 'close < bollinger_lower_20' },
      { field: 'bollinger_percent_b_20', example: 'bollinger_percent_b_20 > 1' },
      { field: 'adx_14', example: 'adx_14 > 25' },
      { field: 'plus_di_14', example: 'plus_di_14 > minus_di_14' },
      { field: 'minus_di_14', example: 'minus_di_14 > plus_di_14' },
    ],
  },
  {
    key: 'volumeIndicators',
    fields: [
      { field: 'obv', example: 'obv > 0' },
      { field: 'vwap', example: 'close > vwap' },
      { field: 'mfi_14', example: 'mfi_14 < 20' },
    ],
  },
  {
    key: 'trendAdvanced',
    fields: [
      { field: 'ichimoku_tenkan_sen', example: 'close > ichimoku_tenkan_sen' },
      { field: 'ichimoku_kijun_sen', example: 'close > ichimoku_kijun_sen' },
      { field: 'supertrend', example: 'close > supertrend' },
      { field: 'supertrend_direction', example: 'supertrend_direction > 0' },
      { field: 'pivot', example: 'close > pivot' },
      { field: 'pivot_r1', example: 'close > pivot_r1' },
      { field: 'pivot_s1', example: 'close < pivot_s1' },
      { field: 'support_20', example: 'close < support_20' },
      { field: 'resistance_20', example: 'close > resistance_20' },
    ],
  },
  {
    key: 'patterns',
    fields: [
      { field: 'pattern_doji', example: 'pattern_doji > 0' },
      { field: 'pattern_hammer', example: 'pattern_hammer > 0' },
      { field: 'pattern_shooting_star', example: 'pattern_shooting_star > 0' },
      { field: 'pattern_bullish_engulfing', example: 'pattern_bullish_engulfing > 0' },
      { field: 'pattern_bearish_engulfing', example: 'pattern_bearish_engulfing > 0' },
    ],
  },
  {
    key: 'fundamentals',
    fields: [
      { field: 'pe', example: 'pe < 15' },
      { field: 'pbv', example: 'pbv < 3' },
      { field: 'roe', example: 'roe > 0.15' },
      { field: 'roa', example: 'roa > 0' },
      { field: 'roic', example: 'roic > 0.10' },
      { field: 'revenue_growth', example: 'revenue_growth > 0' },
      { field: 'debt_to_equity', example: 'debt_to_equity < 1' },
      { field: 'current_ratio', example: 'current_ratio > 1' },
      { field: 'dividend_yield', example: 'dividend_yield > 0.02' },
    ],
  },
]

function CopyButton({ text }) {
  const { t } = useLanguage()
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      // Fallback for environments without clipboard permission.
      const textarea = document.createElement('textarea')
      textarea.value = text
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 1200)
  }

  return (
    <button type="button" onClick={handleCopy}>
      {copied ? t('formulaReference.copied') : t('formulaReference.copy')}
    </button>
  )
}

export default function FormulaReference() {
  const { t } = useLanguage()

  return (
    <details className="formula-reference">
      <summary>{t('formulaReference.title')}</summary>
      <p className="page-hint">{t('formulaReference.hint')}</p>
      {GROUPS.map((group) => (
        <div key={group.key} className="formula-reference-group">
          <h4>{t(`formulaReference.groups.${group.key}`)}</h4>
          {group.fields.map((row) => (
            <div key={row.field} className="formula-reference-row">
              <code>{row.field}</code>
              <code>{row.example}</code>
              <CopyButton text={row.example} />
            </div>
          ))}
        </div>
      ))}
    </details>
  )
}
