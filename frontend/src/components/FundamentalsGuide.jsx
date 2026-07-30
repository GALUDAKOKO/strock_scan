import { useLanguage } from '../i18n/LanguageContext.jsx'

const METRIC_KEYS = [
  'price',
  'pe',
  'pbv',
  'roe',
  'roa',
  'revenueGrowth',
  'piotroski',
  'altman',
  'beneish',
]

export default function FundamentalsGuide() {
  const { t } = useLanguage()

  return (
    <details className="formula-reference">
      <summary>{t('fundamentals.guide.title')}</summary>
      <p className="page-hint">{t('fundamentals.guide.hint')}</p>
      <div className="fundamentals-guide-list">
        {METRIC_KEYS.map((key) => (
          <div key={key} className="fundamentals-guide-item">
            <h4>{t(`fundamentals.guide.${key}.term`)}</h4>
            <p>{t(`fundamentals.guide.${key}.meaning`)}</p>
            <p className="fundamentals-guide-read">{t(`fundamentals.guide.${key}.howToRead`)}</p>
          </div>
        ))}
      </div>
    </details>
  )
}
