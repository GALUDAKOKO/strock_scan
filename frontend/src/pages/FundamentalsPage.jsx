import { useState } from 'react'
import { api, parseSymbols } from '../api.js'
import ResultsTable from '../components/ResultsTable.jsx'
import SymbolsInput from '../components/SymbolsInput.jsx'
import WatchlistPicker from '../components/WatchlistPicker.jsx'
import ExportButtons from '../components/ExportButtons.jsx'
import { useLanguage } from '../i18n/LanguageContext.jsx'
import { formatUpdatedAt } from '../utils/format.js'
import FundamentalsGuide from '../components/FundamentalsGuide.jsx'

function formatMetric(value) {
  if (value === null || value === undefined) return '-'
  return Number.isInteger(value) ? value.toString() : value.toFixed(4)
}

export default function FundamentalsPage({ active = true }) {
  const { t } = useLanguage()
  const [symbolsRaw, setSymbolsRaw] = useState('AAPL, MSFT')
  const [refresh, setRefresh] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [results, setResults] = useState(null)
  const [selectedSymbol, setSelectedSymbol] = useState(null)

  const comparisonColumns = [
    { key: 'symbol', label: t('common.symbol') },
    { key: 'price', label: t('metricLabels.price'), get: (row) => row.metrics?.price },
    { key: 'pe', label: t('metricLabels.pe'), get: (row) => row.metrics?.pe },
    { key: 'pbv', label: t('metricLabels.pbv'), get: (row) => row.metrics?.pbv },
    { key: 'roe', label: t('metricLabels.roe'), get: (row) => row.metrics?.roe },
    { key: 'roa', label: t('metricLabels.roa'), get: (row) => row.metrics?.roa },
    { key: 'revenue_growth', label: t('metricLabels.revenue_growth'), get: (row) => row.metrics?.revenue_growth },
    { key: 'piotroski_f_score', label: t('fundamentals.piotroski') },
    { key: 'altman_z_score', label: t('fundamentals.altman') },
    { key: 'beneish_m_score', label: t('fundamentals.beneish') },
    { key: 'error', label: t('screener.columns.error') },
    { key: 'updated_at', label: t('common.updatedAt'), get: (row) => formatUpdatedAt(row.updated_at) },
  ]

  async function load() {
    setError(null)
    setLoading(true)
    setResults(null)
    setSelectedSymbol(null)
    try {
      const symbols = parseSymbols(symbolsRaw)
      if (symbols.length === 0) throw new Error(t('fundamentals.enterSymbol'))

      const settled = await Promise.allSettled(symbols.map((symbol) => api.fundamentals(symbol, refresh)))

      const rows = settled.map((outcome, index) => {
        const symbol = symbols[index]
        if (outcome.status === 'fulfilled') {
          return outcome.value
        }
        return { symbol, error: outcome.reason?.message || String(outcome.reason), metrics: {} }
      })

      setResults(rows)
      const firstOk = rows.find((row) => !row.error)
      setSelectedSymbol(firstOk ? firstOk.symbol : rows[0]?.symbol || null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const selectedResult = results?.find((row) => row.symbol === selectedSymbol) || null

  return (
    <section className="page">
      <h2>{t('fundamentals.title')}</h2>
      <p className="page-hint">{t('fundamentals.hint')}</p>

      <FundamentalsGuide />

      <SymbolsInput value={symbolsRaw} onChange={setSymbolsRaw} />
      <WatchlistPicker onLoad={setSymbolsRaw} active={active} />

      <div className="form-row">
        <label className="filter-checkbox">
          <input type="checkbox" checked={refresh} onChange={(e) => setRefresh(e.target.checked)} />
          <span>{t('common.forceRefresh')}</span>
        </label>
        <button onClick={load} disabled={loading}>
          {loading ? t('fundamentals.loading') : t('fundamentals.load')}
        </button>
      </div>

      {error && <p className="error-message">{error}</p>}

      {results && (
        <>
          <p className="page-hint">{t('fundamentals.sortHint')}</p>
          <ResultsTable columns={comparisonColumns} rows={results} sortable />

          {results.length > 1 && (
            <div className="form-row">
              <label>
                {t('backtest.viewDetail')}
                <select value={selectedSymbol || ''} onChange={(e) => setSelectedSymbol(e.target.value)}>
                  {results.map((row) => (
                    <option key={row.symbol} value={row.symbol}>
                      {row.symbol}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {selectedResult && !selectedResult.error && (
            <>
              <div className="metric-cards">
                <div className="metric-card">
                  <span className="metric-label">{t('fundamentals.piotroski')}</span>
                  <span className="metric-value">{selectedResult.piotroski_f_score ?? '-'} / 9</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">{t('fundamentals.altman')}</span>
                  <span className="metric-value">{formatMetric(selectedResult.altman_z_score)}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">{t('fundamentals.beneish')}</span>
                  <span className="metric-value">{formatMetric(selectedResult.beneish_m_score)}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">{t('common.updatedAt')}</span>
                  <span className="metric-value">{formatUpdatedAt(selectedResult.updated_at)}</span>
                </div>
              </div>

              <div className="table-wrapper">
                <table className="results-table">
                  <thead>
                    <tr>
                      <th>{t('common.metric')}</th>
                      <th>{t('common.value')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(selectedResult.metrics).map(([key, value]) => (
                      <tr key={key}>
                        <td>{t(`metricLabels.${key}`)}</td>
                        <td>{formatMetric(value)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          <ExportButtons
            spec={{
              title: t('fundamentals.title'),
              subtitle: symbolsRaw,
              generatedAtLabel: t('export.generatedAt'),
              generatedAt: new Date().toLocaleString(),
              meta: [{ label: t('common.symbol'), value: symbolsRaw }],
              sections: [
                {
                  type: 'table',
                  heading: t('fundamentals.title'),
                  table: { columns: comparisonColumns, rows: results, emptyMessage: t('common.noResults') },
                },
                ...(selectedResult && !selectedResult.error
                  ? [
                      {
                        type: 'cards',
                        heading: selectedResult.symbol,
                        cards: [
                          { label: t('fundamentals.piotroski'), value: `${selectedResult.piotroski_f_score ?? '-'} / 9` },
                          { label: t('fundamentals.altman'), value: formatMetric(selectedResult.altman_z_score) },
                          { label: t('fundamentals.beneish'), value: formatMetric(selectedResult.beneish_m_score) },
                        ],
                      },
                      {
                        type: 'table',
                        heading: `${selectedResult.symbol} ${t('common.metric')}`,
                        table: {
                          columns: [
                            { key: 'metric', label: t('common.metric') },
                            { key: 'value', label: t('common.value') },
                          ],
                          rows: Object.entries(selectedResult.metrics).map(([key, value]) => ({
                            metric: t(`metricLabels.${key}`),
                            value: formatMetric(value),
                          })),
                        },
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
