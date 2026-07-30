import { useLanguage } from '../i18n/LanguageContext.jsx'

const METRIC_KEYS = [
  'finalEquity',
  'totalReturn',
  'cagr',
  'maxDrawdown',
  'sharpeRatio',
  'winRate',
  'profitFactor',
  'trades',
  'commission',
  'slippage',
]

export default function BacktestGuide() {
  const { t } = useLanguage()

  return (
    <details className="formula-reference">
      <summary>{t('backtest.guide.title')}</summary>
      <p className="page-hint">{t('backtest.guide.hint')}</p>
      <div className="fundamentals-guide-list">
        {METRIC_KEYS.map((key) => (
          <div key={key} className="fundamentals-guide-item">
            <h4>{t(`backtest.guide.${key}.term`)}</h4>
            <p>{t(`backtest.guide.${key}.meaning`)}</p>
            <p className="fundamentals-guide-read">{t(`backtest.guide.${key}.howToRead`)}</p>
          </div>
        ))}
      </div>
    </details>
  )
}
