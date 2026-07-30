import { useLanguage } from '../i18n/LanguageContext.jsx'

const METRIC_KEYS = ['grahamNumber', 'grahamMOS', 'dcfFairValue', 'dcfMOS']

export default function ValuationGuide() {
  const { t } = useLanguage()

  return (
    <details className="formula-reference">
      <summary>{t('valuation.guide.title')}</summary>
      <p className="page-hint">{t('valuation.guide.hint')}</p>
      <div className="fundamentals-guide-list">
        {METRIC_KEYS.map((key) => (
          <div key={key} className="fundamentals-guide-item">
            <h4>{t(`valuation.guide.${key}.term`)}</h4>
            <p>{t(`valuation.guide.${key}.meaning`)}</p>
            <p className="fundamentals-guide-read">{t(`valuation.guide.${key}.howToRead`)}</p>
          </div>
        ))}
      </div>
    </details>
  )
}
