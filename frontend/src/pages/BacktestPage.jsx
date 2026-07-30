import { useState } from 'react'
import { api, parseSymbols } from '../api.js'
import ResultsTable from '../components/ResultsTable.jsx'
import SymbolsInput from '../components/SymbolsInput.jsx'
import WatchlistPicker from '../components/WatchlistPicker.jsx'
import ExportButtons from '../components/ExportButtons.jsx'
import { useLanguage } from '../i18n/LanguageContext.jsx'
import { formatUpdatedAt } from '../utils/format.js'
import FormulaReference from '../components/FormulaReference.jsx'
import BacktestGuide from '../components/BacktestGuide.jsx'

function fmt(value, suffix = '') {
  if (value === null || value === undefined) return '-'
  return `${Number(value).toFixed(2)}${suffix}`
}

export default function BacktestPage({ active = true }) {
  const { t } = useLanguage()
  const [symbolsRaw, setSymbolsRaw] = useState('AAPL, MSFT')
  const [formula, setFormula] = useState('close > sma_20 AND close > ema_20')
  const [initialCash, setInitialCash] = useState('100000')
  const [commissionPct, setCommissionPct] = useState('0')
  const [slippagePct, setSlippagePct] = useState('0')
  const [refresh, setRefresh] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [results, setResults] = useState(null)
  const [selectedSymbol, setSelectedSymbol] = useState(null)

  const tradeColumns = [
    { key: 'side', label: t('backtest.columns.side') },
    { key: 'timestamp', label: t('backtest.columns.timestamp') },
    { key: 'price', label: t('backtest.columns.price') },
    { key: 'shares', label: t('backtest.columns.shares') },
    { key: 'cash', label: t('backtest.columns.cash') },
  ]

  const summaryColumns = [
    { key: 'symbol', label: t('common.symbol') },
    { key: 'final_equity', label: t('backtest.finalEquity'), get: (row) => row.final_equity },
    { key: 'total_return_pct', label: t('backtest.totalReturn'), get: (row) => row.total_return_pct },
    { key: 'cagr_pct', label: t('backtest.cagr'), get: (row) => row.cagr_pct },
    { key: 'max_drawdown_pct', label: t('backtest.maxDrawdown'), get: (row) => row.max_drawdown_pct },
    { key: 'sharpe_ratio', label: t('backtest.sharpeRatio'), get: (row) => row.sharpe_ratio },
    { key: 'win_rate_pct', label: t('backtest.winRate'), get: (row) => row.win_rate_pct },
    { key: 'profit_factor', label: t('backtest.profitFactor'), get: (row) => row.profit_factor },
    { key: 'trade_count', label: t('backtest.trades'), get: (row) => row.trade_count },
    { key: 'error', label: t('screener.columns.error') },
    { key: 'updated_at', label: t('common.updatedAt'), get: (row) => formatUpdatedAt(row.updated_at) },
  ]

  async function runBacktest() {
    setError(null)
    setLoading(true)
    setResults(null)
    setSelectedSymbol(null)
    try {
      const symbols = parseSymbols(symbolsRaw)
      if (symbols.length === 0) throw new Error(t('backtest.enterSymbol'))
      if (!formula.trim()) throw new Error(t('backtest.enterFormula'))

      const settled = await Promise.allSettled(
        symbols.map((symbol) =>
          api.backtest({
            symbol,
            formula: formula.trim(),
            initial_cash: Number(initialCash) || 100000,
            commission_pct: Number(commissionPct) / 100 || 0,
            slippage_pct: Number(slippagePct) / 100 || 0,
            refresh,
          })
        )
      )

      const rows = settled.map((outcome, index) => {
        const symbol = symbols[index]
        if (outcome.status === 'fulfilled') {
          return { ...outcome.value, symbol }
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
      <h2>{t('backtest.title')}</h2>
      <p className="page-hint">{t('backtest.hint')}</p>

      <BacktestGuide />

      <SymbolsInput value={symbolsRaw} onChange={setSymbolsRaw} />
      <WatchlistPicker onLoad={setSymbolsRaw} active={active} />

      <div className="form-row">
        <label>
          {t('backtest.initialCash')}
          <input type="number" value={initialCash} onChange={(e) => setInitialCash(e.target.value)} />
        </label>
        <label>
          {t('backtest.commissionPct')}
          <input
            type="number"
            step="0.01"
            min="0"
            value={commissionPct}
            onChange={(e) => setCommissionPct(e.target.value)}
          />
        </label>
        <label>
          {t('backtest.slippagePct')}
          <input
            type="number"
            step="0.01"
            min="0"
            value={slippagePct}
            onChange={(e) => setSlippagePct(e.target.value)}
          />
        </label>
        <label className="filter-checkbox">
          <input type="checkbox" checked={refresh} onChange={(e) => setRefresh(e.target.checked)} />
          <span>{t('common.forceRefresh')}</span>
        </label>
      </div>

      <div className="custom-formula">
        <label htmlFor="backtest-formula">{t('backtest.formula')}</label>
        <input
          id="backtest-formula"
          type="text"
          value={formula}
          onChange={(e) => setFormula(e.target.value)}
        />
      </div>

      <FormulaReference />

      <div className="form-row">
        <button onClick={runBacktest} disabled={loading}>
          {loading ? t('backtest.running') : t('backtest.run')}
        </button>
      </div>

      {error && <p className="error-message">{error}</p>}

      {results && (
        <>
          <ResultsTable columns={summaryColumns} rows={results} />

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
                  <span className="metric-label">{t('backtest.finalEquity')}</span>
                  <span className="metric-value">{Number(selectedResult.final_equity).toFixed(2)}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">{t('backtest.totalReturn')}</span>
                  <span className="metric-value">{Number(selectedResult.total_return_pct).toFixed(2)}%</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">{t('backtest.cagr')}</span>
                  <span className="metric-value">{fmt(selectedResult.cagr_pct, '%')}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">{t('backtest.maxDrawdown')}</span>
                  <span className="metric-value">{Number(selectedResult.max_drawdown_pct).toFixed(2)}%</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">{t('backtest.sharpeRatio')}</span>
                  <span className="metric-value">{fmt(selectedResult.sharpe_ratio)}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">{t('backtest.winRate')}</span>
                  <span className="metric-value">{fmt(selectedResult.win_rate_pct, '%')}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">{t('backtest.profitFactor')}</span>
                  <span className="metric-value">{fmt(selectedResult.profit_factor)}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">{t('backtest.trades')}</span>
                  <span className="metric-value">{selectedResult.trade_count}</span>
                </div>
                <div className="metric-card">
                  <span className="metric-label">{t('common.updatedAt')}</span>
                  <span className="metric-value">{formatUpdatedAt(selectedResult.updated_at)}</span>
                </div>
              </div>
              {selectedResult.error && <p className="error-message">{selectedResult.error}</p>}
              <ResultsTable columns={tradeColumns} rows={selectedResult.trades} emptyMessage={t('common.noTrades')} />
            </>
          )}

          <ExportButtons
            spec={{
              title: t('backtest.title'),
              subtitle: formula.trim(),
              generatedAtLabel: t('export.generatedAt'),
              generatedAt: new Date().toLocaleString(),
              meta: [
                { label: t('common.symbol'), value: symbolsRaw },
                { label: t('backtest.formula'), value: formula.trim() },
                { label: t('backtest.initialCash'), value: initialCash },
                { label: t('backtest.commissionPct'), value: `${commissionPct}%` },
                { label: t('backtest.slippagePct'), value: `${slippagePct}%` },
              ],
              sections: [
                {
                  type: 'table',
                  heading: t('backtest.title'),
                  table: { columns: summaryColumns, rows: results, emptyMessage: t('common.noResults') },
                },
                ...(selectedResult && !selectedResult.error
                  ? [
                      {
                        type: 'cards',
                        heading: selectedResult.symbol,
                        cards: [
                          { label: t('backtest.finalEquity'), value: Number(selectedResult.final_equity).toFixed(2) },
                          {
                            label: t('backtest.totalReturn'),
                            value: `${Number(selectedResult.total_return_pct).toFixed(2)}%`,
                          },
                          { label: t('backtest.cagr'), value: fmt(selectedResult.cagr_pct, '%') },
                          {
                            label: t('backtest.maxDrawdown'),
                            value: `${Number(selectedResult.max_drawdown_pct).toFixed(2)}%`,
                          },
                          { label: t('backtest.sharpeRatio'), value: fmt(selectedResult.sharpe_ratio) },
                          { label: t('backtest.winRate'), value: fmt(selectedResult.win_rate_pct, '%') },
                          { label: t('backtest.profitFactor'), value: fmt(selectedResult.profit_factor) },
                          { label: t('backtest.trades'), value: selectedResult.trade_count },
                        ],
                      },
                      {
                        type: 'table',
                        heading: `${selectedResult.symbol} ${t('backtest.trades')}`,
                        table: {
                          columns: tradeColumns,
                          rows: selectedResult.trades,
                          emptyMessage: t('common.noTrades'),
                        },
                      },
                    ]
                  : []),
              ],
              labels: { yes: t('common.yes'), no: t('common.no') },
            }}
          />
        </>
      )}
    </section>
  )
}
