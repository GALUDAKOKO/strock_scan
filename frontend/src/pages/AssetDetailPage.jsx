import { useState } from 'react'
import { api } from '../api.js'
import PriceChart from '../components/PriceChart.jsx'
import ExportButtons from '../components/ExportButtons.jsx'
import { useLanguage } from '../i18n/LanguageContext.jsx'
import { formatUpdatedAt } from '../utils/format.js'

const TECHNICAL_ROWS = [
  'close',
  'sma_20',
  'ema_20',
  'rsi_14',
  'momentum_score',
  'macd',
  'macd_signal',
  'macd_histogram',
  'cci_20',
  'atr_14',
  'adx_14',
  'plus_di_14',
  'minus_di_14',
  'bollinger_upper_20',
  'bollinger_middle_20',
  'bollinger_lower_20',
  'obv',
  'vwap',
  'mfi_14',
  'ichimoku_tenkan_sen',
  'ichimoku_kijun_sen',
  'supertrend',
  'supertrend_direction',
  'pivot',
  'support_20',
  'resistance_20',
]

const PATTERN_ROWS = [
  'pattern_doji',
  'pattern_hammer',
  'pattern_shooting_star',
  'pattern_bullish_engulfing',
  'pattern_bearish_engulfing',
]

function formatMetric(value) {
  if (value === null || value === undefined) return '-'
  return Number.isInteger(value) ? value.toString() : Number(value).toFixed(4)
}

export default function AssetDetailPage() {
  const { t } = useLanguage()
  const [symbol, setSymbol] = useState('AAPL')
  const [refresh, setRefresh] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [asset, setAsset] = useState(null)
  const [history, setHistory] = useState(null)
  const [technicals, setTechnicals] = useState(null)
  const [fundamentals, setFundamentals] = useState(null)

  async function load() {
    setError(null)
    if (!symbol.trim()) {
      setError(t('assetDetail.enterSymbol'))
      return
    }
    setLoading(true)
    setAsset(null)
    setHistory(null)
    setTechnicals(null)
    setFundamentals(null)
    try {
      const [assetResult, historyResult, technicalsResult, fundamentalsResult] = await Promise.allSettled([
        api.assetInfo(symbol, refresh),
        api.history(symbol, { refresh }),
        api.technicals(symbol, refresh),
        api.fundamentals(symbol, refresh),
      ])

      setAsset(assetResult.status === 'fulfilled' ? assetResult.value : { error: assetResult.reason?.message })
      setHistory(historyResult.status === 'fulfilled' ? historyResult.value : [])
      setTechnicals(technicalsResult.status === 'fulfilled' ? technicalsResult.value : null)
      setFundamentals(fundamentalsResult.status === 'fulfilled' ? fundamentalsResult.value : null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const activePatterns = technicals
    ? PATTERN_ROWS.filter((key) => Number(technicals.metrics?.[key]) > 0)
    : []

  return (
    <section className="page">
      <h2>{t('assetDetail.title')}</h2>
      <p className="page-hint">{t('assetDetail.hint')}</p>

      <div className="form-row">
        <label>
          {t('common.symbol')}
          <input
            type="text"
            value={symbol}
            placeholder={t('assetDetail.symbolPlaceholder')}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          />
        </label>
        <label className="filter-checkbox">
          <input type="checkbox" checked={refresh} onChange={(e) => setRefresh(e.target.checked)} />
          <span>{t('common.forceRefresh')}</span>
        </label>
        <button onClick={load} disabled={loading}>
          {loading ? t('assetDetail.loading') : t('assetDetail.load')}
        </button>
      </div>

      {error && <p className="error-message">{error}</p>}

      {asset && !asset.error && (
        <>
          <h3>{t('assetDetail.overview')}</h3>
          <div className="asset-summary-cards">
            <div className="metric-card">
              <span className="metric-label">{t('common.symbol')}</span>
              <span className="metric-value">{asset.symbol}</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">{asset.name || t('assetDetail.overview')}</span>
              <span className="metric-value">{asset.market || '-'}</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">{t('assetDetail.assetType')}</span>
              <span className="metric-value">{asset.asset_type || '-'}</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">{t('assetDetail.currency')}</span>
              <span className="metric-value">{asset.currency || '-'}</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">{t('common.updatedAt')}</span>
              <span className="metric-value">{formatUpdatedAt(asset.updated_at)}</span>
            </div>
          </div>

          <h3>{t('assetDetail.priceChart')}</h3>
          <PriceChart candles={history} emptyMessage={t('common.noResults')} />

          {technicals && (
            <>
              <h3>{t('assetDetail.technicals')}</h3>
              <div className="table-wrapper">
                <table className="results-table">
                  <thead>
                    <tr>
                      <th>{t('common.metric')}</th>
                      <th>{t('common.value')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {TECHNICAL_ROWS.map((key) => (
                      <tr key={key}>
                        <td>{t(`technicalLabels.${key}`)}</td>
                        <td>{formatMetric(technicals.metrics?.[key])}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <h3>{t('assetDetail.patterns')}</h3>
              {activePatterns.length > 0 ? (
                <ul>
                  {activePatterns.map((key) => (
                    <li key={key}>{t(`technicalLabels.${key}`)}</li>
                  ))}
                </ul>
              ) : (
                <p className="empty-message">{t('assetDetail.noPatterns')}</p>
              )}
            </>
          )}

          {fundamentals && !fundamentals.error && (
            <>
              <h3>{t('assetDetail.fundamentalsSnapshot')}</h3>
              <div className="asset-summary-cards">
                <div className="metric-card">
                  <span className="metric-label">{t('metricLabels.price')}</span>
                  <span className="metric-value">{formatMetric(fundamentals.metrics?.price)}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">{t('metricLabels.pe')}</span>
                  <span className="metric-value">{formatMetric(fundamentals.metrics?.pe)}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">{t('metricLabels.pbv')}</span>
                  <span className="metric-value">{formatMetric(fundamentals.metrics?.pbv)}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">{t('metricLabels.roe')}</span>
                  <span className="metric-value">{formatMetric(fundamentals.metrics?.roe)}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">{t('metricLabels.roa')}</span>
                  <span className="metric-value">{formatMetric(fundamentals.metrics?.roa)}</span>
                </div>
              </div>
            </>
          )}

          <ExportButtons
            spec={{
              title: t('assetDetail.title'),
              subtitle: asset.symbol,
              generatedAtLabel: t('export.generatedAt'),
              generatedAt: new Date().toLocaleString(),
              meta: [
                { label: t('common.symbol'), value: asset.symbol },
                { label: t('assetDetail.market'), value: asset.market || '-' },
                { label: t('common.updatedAt'), value: formatUpdatedAt(asset.updated_at) },
              ],
              sections: [
                ...(technicals
                  ? [
                      {
                        type: 'table',
                        heading: t('assetDetail.technicals'),
                        table: {
                          columns: [
                            { key: 'metric', label: t('common.metric') },
                            { key: 'value', label: t('common.value') },
                          ],
                          rows: TECHNICAL_ROWS.map((key) => ({
                            metric: t(`technicalLabels.${key}`),
                            value: formatMetric(technicals.metrics?.[key]),
                          })),
                        },
                      },
                    ]
                  : []),
                ...(fundamentals && !fundamentals.error
                  ? [
                      {
                        type: 'cards',
                        heading: t('assetDetail.fundamentalsSnapshot'),
                        cards: [
                          { label: t('metricLabels.price'), value: formatMetric(fundamentals.metrics?.price) },
                          { label: t('metricLabels.pe'), value: formatMetric(fundamentals.metrics?.pe) },
                          { label: t('metricLabels.pbv'), value: formatMetric(fundamentals.metrics?.pbv) },
                          { label: t('metricLabels.roe'), value: formatMetric(fundamentals.metrics?.roe) },
                          { label: t('metricLabels.roa'), value: formatMetric(fundamentals.metrics?.roa) },
                        ],
                      },
                    ]
                  : []),
              ],
            }}
          />
        </>
      )}
    </section>
  )
}
