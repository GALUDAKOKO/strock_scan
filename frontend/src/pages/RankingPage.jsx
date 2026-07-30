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

const SORT_OPTIONS = [
  'momentum_score',
  'close_vs_sma_20',
  'close_vs_ema_20',
  'rsi_14',
  'close',
  'volume',
  'pe',
  'roe',
  'revenue_growth',
  'score_overall',
  'score_quality',
  'score_growth',
  'score_value',
  'score_momentum',
  'score_risk',
]

export default function RankingPage({ active = true }) {
  const { t } = useLanguage()
  const [symbolsRaw, setSymbolsRaw] = useState('AAPL, MSFT, GOOGL')
  const [sortBy, setSortBy] = useState('momentum_score')
  const [descending, setDescending] = useState(true)
  const [limit, setLimit] = useState('')
  const [selected, setSelected] = useState(new Set())
  const [customFormula, setCustomFormula] = useState('')
  const [sector, setSector] = useState('')
  const [assetType, setAssetType] = useState('')
  const [includeFundamentals, setIncludeFundamentals] = useState(false)
  const [refresh, setRefresh] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const columns = [
    { key: 'rank', label: t('ranking.columns.rank') },
    { key: 'symbol', label: t('ranking.columns.symbol') },
    { key: 'score', label: t('ranking.columns.score') },
    { key: 'passed_filter', label: t('ranking.columns.passedFilter') },
    { key: 'close', label: t('ranking.columns.close'), get: (row) => row.metrics?.close },
    { key: 'score_overall', label: t('ranking.columns.scoreOverall'), get: (row) => row.metrics?.score_overall },
    { key: 'score_quality', label: t('ranking.columns.scoreQuality'), get: (row) => row.metrics?.score_quality },
    { key: 'score_growth', label: t('ranking.columns.scoreGrowth'), get: (row) => row.metrics?.score_growth },
    { key: 'score_value', label: t('ranking.columns.scoreValue'), get: (row) => row.metrics?.score_value },
    { key: 'score_momentum', label: t('ranking.columns.scoreMomentum'), get: (row) => row.metrics?.score_momentum },
    { key: 'score_risk', label: t('ranking.columns.scoreRisk'), get: (row) => row.metrics?.score_risk },
    { key: 'error', label: t('ranking.columns.error') },
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

  async function runRank() {
    setError(null)
    setLoading(true)
    try {
      const all = [...TECHNICAL_FILTERS, ...FUNDAMENTAL_FILTERS]
      const selectedExprs = all.filter((filter) => selected.has(filter.id)).map((filter) => filter.expr)
      if (sector) selectedExprs.push(`sector = "${sector}"`)
      if (assetType) selectedExprs.push(`asset_type = "${assetType}"`)
      const formula = buildFormula(selectedExprs, customFormula) || null
      const symbols = parseSymbols(symbolsRaw)
      if (symbols.length === 0) {
        throw new Error(t('ranking.enterSymbol'))
      }
      const response = await api.rank({
        symbols,
        sort_by: sortBy,
        descending,
        formula,
        limit: limit ? Number(limit) : undefined,
        include_fundamentals: Boolean(includeFundamentals || sortBy.match(/pe|roe|roa|revenue_growth|pbv|score_/)),
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
      <h2>{t('ranking.title')}</h2>
      <p className="page-hint">{t('ranking.hint')}</p>

      <SymbolsInput value={symbolsRaw} onChange={setSymbolsRaw} />
      <WatchlistPicker onLoad={setSymbolsRaw} active={active} />

      <div className="form-row">
        <label>
          {t('ranking.sortBy')}
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            {SORT_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-checkbox">
          <input type="checkbox" checked={descending} onChange={(e) => setDescending(e.target.checked)} />
          <span>{t('ranking.descending')}</span>
        </label>
        <label>
          {t('ranking.limit')}
          <input
            type="number"
            min="1"
            placeholder={t('ranking.limitPlaceholder')}
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
          />
        </label>
      </div>

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
        <button onClick={runRank} disabled={loading}>
          {loading ? t('ranking.running') : t('ranking.run')}
        </button>
      </div>

      {error && <p className="error-message">{error}</p>}

      {result && (
        <>
          <p className="result-summary">{t('ranking.summary', result.sort_by, result.ranked, result.count)}</p>
          <ResultsTable columns={columns} rows={result.results} />
          <ExportButtons
            spec={{
              title: t('ranking.title'),
              subtitle: t('ranking.summary', result.sort_by, result.ranked, result.count),
              generatedAtLabel: t('export.generatedAt'),
              generatedAt: new Date().toLocaleString(),
              meta: [
                { label: t('ranking.columns.symbol'), value: symbolsRaw },
                { label: t('ranking.sortBy'), value: result.sort_by },
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
