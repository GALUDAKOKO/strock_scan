import { useState } from 'react'
import { api, parseSymbols } from '../api.js'
import ResultsTable from '../components/ResultsTable.jsx'
import SymbolsInput from '../components/SymbolsInput.jsx'
import WatchlistPicker from '../components/WatchlistPicker.jsx'
import ExportButtons from '../components/ExportButtons.jsx'
import { useLanguage } from '../i18n/LanguageContext.jsx'
import { formatUpdatedAt } from '../utils/format.js'
import ValuationGuide from '../components/ValuationGuide.jsx'

function formatMetric(value, suffix = '') {
  if (value === null || value === undefined) return '-'
  return `${Number(value).toFixed(2)}${suffix}`
}

export default function ValuationPage({ active = true }) {
  const { t } = useLanguage()
  const [symbolsRaw, setSymbolsRaw] = useState('AAPL, MSFT')
  const [growthRate, setGrowthRate] = useState('0.08')
  const [discountRate, setDiscountRate] = useState('0.10')
  const [terminalGrowth, setTerminalGrowth] = useState('0.025')
  const [years, setYears] = useState('5')
  const [refresh, setRefresh] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [results, setResults] = useState(null)
  const [selectedSymbol, setSelectedSymbol] = useState(null)

  const comparisonColumns = [
    { key: 'symbol', label: t('common.symbol') },
    { key: 'price', label: t('valuation.currentPrice') },
    { key: 'graham_number', label: t('valuation.grahamNumber') },
    { key: 'graham_margin_of_safety_pct', label: t('valuation.grahamMOS') },
    { key: 'dcf_fair_value', label: t('valuation.dcfFairValue') },
    { key: 'dcf_margin_of_safety_pct', label: t('valuation.dcfMOS') },
    { key: 'error', label: t('screener.columns.error') },
    { key: 'updated_at', label: t('common.updatedAt'), get: (row) => formatUpdatedAt(row.updated_at) },
  ]

  async function runValuation() {
    setError(null)
    setLoading(true)
    setResults(null)
    setSelectedSymbol(null)
    try {
      const symbols = parseSymbols(symbolsRaw)
      if (symbols.length === 0) throw new Error(t('valuation.enterSymbol'))

      const settled = await Promise.allSettled(
        symbols.map((symbol) =>
          api.valuation({
            symbol,
            growth_rate: Number(growthRate),
            discount_rate: Number(discountRate),
            terminal_growth: Number(terminalGrowth),
            years: Number(years),
            refresh,
          })
        )
      )

      const rows = settled.map((outcome, index) => {
        const symbol = symbols[index]
        if (outcome.status === 'fulfilled') {
          const value = outcome.value
          return value.error ? { symbol, error: value.error } : value
        }
        return { symbol, error: outcome.reason?.message || String(outcome.reason) }
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
      <h2>{t('valuation.title')}</h2>
      <p className="page-hint">{t('valuation.hint')}</p>

      <ValuationGuide />

      <SymbolsInput value={symbolsRaw} onChange={setSymbolsRaw} />
      <WatchlistPicker onLoad={setSymbolsRaw} active={active} />

      <div className="form-row">
        <label>
          {t('valuation.growthRate')}
          <input type="number" step="0.01" value={growthRate} onChange={(e) => setGrowthRate(e.target.value)} />
        </label>
        <label>
          {t('valuation.discountRate')}
          <input type="number" step="0.01" value={discountRate} onChange={(e) => setDiscountRate(e.target.value)} />
        </label>
        <label>
          {t('valuation.terminalGrowth')}
          <input
            type="number"
            step="0.005"
            value={terminalGrowth}
            onChange={(e) => setTerminalGrowth(e.target.value)}
          />
        </label>
        <label>
          {t('valuation.years')}
          <input type="number" min="1" value={years} onChange={(e) => setYears(e.target.value)} />
        </label>
        <label className="filter-checkbox">
          <input type="checkbox" checked={refresh} onChange={(e) => setRefresh(e.target.checked)} />
          <span>{t('common.forceRefresh')}</span>
        </label>
      </div>

      <div className="form-row">
        <button onClick={runValuation} disabled={loading}>
          {loading ? t('valuation.running') : t('valuation.run')}
        </button>
      </div>

      {error && <p className="error-message">{error}</p>}

      {results && (
        <>
          <p className="page-hint">{t('valuation.sortHint')}</p>
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
            <div className="metric-cards">
              <div className="metric-card">
                <span className="metric-label">{t('valuation.currentPrice')}</span>
                <span className="metric-value">{formatMetric(selectedResult.price)}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">{t('valuation.grahamNumber')}</span>
                <span className="metric-value">{formatMetric(selectedResult.graham_number)}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">{t('valuation.grahamMOS')}</span>
                <span className="metric-value">{formatMetric(selectedResult.graham_margin_of_safety_pct, '%')}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">{t('valuation.dcfFairValue')}</span>
                <span className="metric-value">{formatMetric(selectedResult.dcf_fair_value)}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">{t('valuation.dcfMOS')}</span>
                <span className="metric-value">{formatMetric(selectedResult.dcf_margin_of_safety_pct, '%')}</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">{t('common.updatedAt')}</span>
                <span className="metric-value">{formatUpdatedAt(selectedResult.updated_at)}</span>
              </div>
            </div>
          )}

          <ExportButtons
            spec={{
              title: t('valuation.title'),
              subtitle: symbolsRaw,
              generatedAtLabel: t('export.generatedAt'),
              generatedAt: new Date().toLocaleString(),
              meta: [
                { label: t('common.symbol'), value: symbolsRaw },
                { label: t('valuation.growthRate'), value: growthRate },
                { label: t('valuation.discountRate'), value: discountRate },
                { label: t('valuation.terminalGrowth'), value: terminalGrowth },
                { label: t('valuation.years'), value: years },
              ],
              sections: [
                {
                  type: 'table',
                  heading: t('valuation.title'),
                  table: { columns: comparisonColumns, rows: results, emptyMessage: t('common.noResults') },
                },
                ...(selectedResult && !selectedResult.error
                  ? [
                      {
                        type: 'cards',
                        heading: selectedResult.symbol,
                        cards: [
                          { label: t('valuation.currentPrice'), value: formatMetric(selectedResult.price) },
                          { label: t('valuation.grahamNumber'), value: formatMetric(selectedResult.graham_number) },
                          {
                            label: t('valuation.grahamMOS'),
                            value: formatMetric(selectedResult.graham_margin_of_safety_pct, '%'),
                          },
                          { label: t('valuation.dcfFairValue'), value: formatMetric(selectedResult.dcf_fair_value) },
                          {
                            label: t('valuation.dcfMOS'),
                            value: formatMetric(selectedResult.dcf_margin_of_safety_pct, '%'),
                          },
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
