import { useState } from 'react'
import { api, parseSymbols } from '../api.js'
import { buildFormula, TECHNICAL_FILTERS, FUNDAMENTAL_FILTERS } from '../filters.js'
import FilterPanel from '../components/FilterPanel.jsx'
import SymbolsInput from '../components/SymbolsInput.jsx'
import ResultsTable from '../components/ResultsTable.jsx'
import WatchlistPicker from '../components/WatchlistPicker.jsx'
import ExportButtons from '../components/ExportButtons.jsx'
import { useLanguage } from '../i18n/LanguageContext.jsx'
import { formatUpdatedAt } from '../utils/format.js'

export default function ScreenerPage({ active = true }) {
  const { t } = useLanguage()
  const [symbolsRaw, setSymbolsRaw] = useState('AAPL, MSFT')
  const [selected, setSelected] = useState(new Set(['close_above_sma20']))
  const [customFormula, setCustomFormula] = useState('')
  const [sector, setSector] = useState('')
  const [assetType, setAssetType] = useState('')
  const [includeFundamentals, setIncludeFundamentals] = useState(false)
  const [refresh, setRefresh] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const columns = [
    { key: 'symbol', label: t('screener.columns.symbol') },
    { key: 'passed', label: t('screener.columns.passed') },
    { key: 'close', label: t('screener.columns.close'), get: (row) => row.metrics?.close },
    { key: 'rsi_14', label: t('screener.columns.rsi'), get: (row) => row.metrics?.rsi_14 },
    { key: 'sma_20', label: t('screener.columns.sma'), get: (row) => row.metrics?.sma_20 },
    { key: 'pe', label: t('screener.columns.pe'), get: (row) => row.metrics?.pe },
    { key: 'roe', label: t('screener.columns.roe'), get: (row) => row.metrics?.roe },
    { key: 'error', label: t('screener.columns.error') },
    { key: 'updated_at', label: t('common.updatedAt'), get: (row) => formatUpdatedAt(row.updated_at) },
  ]

  function toggleFilter(id) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function runScreen() {
    setError(null)
    setLoading(true)
    try {
      const all = [...TECHNICAL_FILTERS, ...FUNDAMENTAL_FILTERS]
      const selectedExprs = all.filter((filter) => selected.has(filter.id)).map((filter) => filter.expr)
      if (sector) selectedExprs.push(`sector = "${sector}"`)
      if (assetType) selectedExprs.push(`asset_type = "${assetType}"`)
      const formula = buildFormula(selectedExprs, customFormula)
      if (!formula) {
        throw new Error(t('screener.selectAtLeastOne'))
      }
      const symbols = parseSymbols(symbolsRaw)
      if (symbols.length === 0) {
        throw new Error(t('screener.enterSymbol'))
      }
      const response = await api.screen({
        symbols,
        formula,
        include_fundamentals: includeFundamentals,
        refresh,
      })
      setResult(response)
    } catch (err) {
      setError(err.message)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="page">
      <h2>{t('screener.title')}</h2>
      <p className="page-hint">{t('screener.hint')}</p>

      <SymbolsInput value={symbolsRaw} onChange={setSymbolsRaw} />
      <WatchlistPicker onLoad={setSymbolsRaw} active={active} />

      <FilterPanel
        selected={selected}
        onToggle={toggleFilter}
        customFormula={customFormula}
        onCustomFormulaChange={setCustomFormula}
        includeFundamentals={includeFundamentals}
        onIncludeFundamentalsChange={setIncludeFundamentals}
        sector={sector}
        onSectorChange={setSector}
        assetType={assetType}
        onAssetTypeChange={setAssetType}
      />

      <div className="form-row">
        <label className="filter-checkbox">
          <input type="checkbox" checked={refresh} onChange={(e) => setRefresh(e.target.checked)} />
          <span>{t('common.forceRefresh')}</span>
        </label>
        <button onClick={runScreen} disabled={loading}>
          {loading ? t('screener.running') : t('screener.run')}
        </button>
      </div>

      {error && <p className="error-message">{error}</p>}

      {result && (
        <>
          <p className="result-summary">{t('screener.summary', result.formula, result.passed, result.count)}</p>
          <ResultsTable columns={columns} rows={result.results} />
          <ExportButtons
            spec={{
              title: t('screener.title'),
              subtitle: t('screener.summary', result.formula, result.passed, result.count),
              generatedAtLabel: t('export.generatedAt'),
              generatedAt: new Date().toLocaleString(),
              meta: [
                { label: t('screener.columns.symbol'), value: symbolsRaw },
                { label: 'Formula', value: result.formula },
              ],
              sections: [
                {
                  type: 'table',
                  table: { columns, rows: result.results, emptyMessage: t('common.noResults') },
                },
              ],
              labels: { yes: t('common.yes'), no: t('common.no') },
            }}
          />
        </>
      )}
    </section>
  )
}
