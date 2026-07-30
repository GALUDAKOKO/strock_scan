import { useEffect, useState } from 'react'
import { api, parseSymbols } from '../api.js'
import { useLanguage } from '../i18n/LanguageContext.jsx'

const PROVIDERS = [
  { value: 'anthropic', label: 'Anthropic (Claude)' },
  { value: 'openai', label: 'OpenAI (GPT)' },
  { value: 'gemini', label: 'Google (Gemini)' },
]

function isNotConfiguredError(message) {
  return typeof message === 'string' && /ANTHROPIC_API_KEY|OPENAI_API_KEY|GEMINI_API_KEY/.test(message)
}

function ErrorOrNotConfigured({ error, t }) {
  if (!error) return null
  if (isNotConfiguredError(error)) {
    return <p className="error-message">{t('ai.notConfigured')}</p>
  }
  return <p className="error-message">{error}</p>
}

function SettingsSection() {
  const { t } = useLanguage()
  const [status, setStatus] = useState(null)
  const [provider, setProvider] = useState('anthropic')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [loadingStatus, setLoadingStatus] = useState(true)

  async function loadStatus() {
    setLoadingStatus(true)
    try {
      const result = await api.getAiSettings()
      setStatus(result)
      if (result.provider) setProvider(result.provider)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoadingStatus(false)
    }
  }

  useEffect(() => {
    loadStatus()
  }, [])

  async function handleSave() {
    setError(null)
    setSaving(true)
    try {
      if (!apiKey.trim()) throw new Error(t('ai.settings.enterKey'))
      await api.saveAiSettings(provider, apiKey.trim(), model.trim())
      setApiKey('')
      await loadStatus()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    setError(null)
    setSaving(true)
    try {
      await api.deleteAiSettings()
      await loadStatus()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="ai-section">
      <h3>{t('ai.settings.title')}</h3>
      <p className="page-hint">{t('ai.settings.hint')}</p>

      {!loadingStatus && status && (
        <p className={status.configured ? 'ai-status-ok' : 'ai-status-bad'}>
          {status.configured
            ? status.source === 'saved'
              ? t('ai.settings.statusSaved', status.provider, status.api_key_masked)
              : t('ai.settings.statusEnv', status.provider)
            : t('ai.settings.statusNone')}
        </p>
      )}

      <div className="form-row">
        <label>
          {t('ai.settings.providerLabel')}
          <select value={provider} onChange={(e) => setProvider(e.target.value)}>
            {PROVIDERS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('ai.settings.apiKeyLabel')}
          <input
            type={showKey ? 'text' : 'password'}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={t('ai.settings.apiKeyPlaceholder')}
            autoComplete="off"
          />
        </label>
        <label className="filter-checkbox">
          <input type="checkbox" checked={showKey} onChange={(e) => setShowKey(e.target.checked)} />
          <span>{t('ai.settings.showKey')}</span>
        </label>
      </div>
      <div className="form-row">
        <label>
          {t('ai.settings.modelLabel')}
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder={t('ai.settings.modelPlaceholder')}
          />
        </label>
      </div>
      <div className="form-row">
        <button onClick={handleSave} disabled={saving}>
          {saving ? t('ai.running') : t('ai.settings.saveButton')}
        </button>
        <button onClick={handleDelete} disabled={saving || !status?.configured || status?.source !== 'saved'}>
          {t('ai.settings.clearButton')}
        </button>
      </div>
      {error && <p className="error-message">{error}</p>}
    </section>
  )
}

function ExplainDebugSection() {
  const { t, language } = useLanguage()
  const [formula, setFormula] = useState('close > sma_20 AND rsi_14 < 30')
  const [explanation, setExplanation] = useState(null)
  const [debugResult, setDebugResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function runExplain() {
    setError(null)
    setLoading(true)
    setExplanation(null)
    setDebugResult(null)
    try {
      const result = await api.aiExplainFormula(formula.trim(), language)
      setExplanation(result.explanation)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function runDebug() {
    setError(null)
    setLoading(true)
    setExplanation(null)
    setDebugResult(null)
    try {
      const result = await api.aiDebugFormula(formula.trim(), language)
      setDebugResult(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="ai-section">
      <h3>{t('ai.explainDebug.title')}</h3>
      <p className="page-hint">{t('ai.explainDebug.hint')}</p>
      <div className="custom-formula">
        <label htmlFor="ai-formula">{t('ai.formulaLabel')}</label>
        <input id="ai-formula" type="text" value={formula} onChange={(e) => setFormula(e.target.value)} />
      </div>
      <div className="form-row">
        <button onClick={runExplain} disabled={loading || !formula.trim()}>
          {t('ai.explainDebug.explainButton')}
        </button>
        <button onClick={runDebug} disabled={loading || !formula.trim()}>
          {t('ai.explainDebug.debugButton')}
        </button>
      </div>
      <ErrorOrNotConfigured error={error} t={t} />
      {explanation && <p className="ai-result">{explanation}</p>}
      {debugResult && (
        <div className="ai-result">
          <p className={debugResult.is_valid ? 'ai-status-ok' : 'ai-status-bad'}>{debugResult.message}</p>
          {debugResult.suggestions.length > 0 && (
            <ul>
              {debugResult.suggestions.map((suggestion, index) => (
                <li key={index}>{suggestion}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  )
}

function SummarySection() {
  const { t, language } = useLanguage()
  const [symbol, setSymbol] = useState('AAPL')
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function runSummarize() {
    setError(null)
    setLoading(true)
    setSummary(null)
    try {
      const cleanSymbol = symbol.trim().toUpperCase()
      if (!cleanSymbol) throw new Error(t('ai.summary.enterSymbol'))
      const [technicals, fundamentals] = await Promise.all([
        api.technicals(cleanSymbol).catch(() => null),
        api.fundamentals(cleanSymbol).catch(() => null),
      ])
      const metrics = { ...(technicals?.metrics || {}), ...(fundamentals || {}) }
      const result = await api.aiSummarize(cleanSymbol, metrics, language)
      setSummary(result.summary)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="ai-section">
      <h3>{t('ai.summary.title')}</h3>
      <p className="page-hint">{t('ai.summary.hint')}</p>
      <div className="form-row">
        <label>
          {t('common.symbol')}
          <input type="text" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
        </label>
        <button onClick={runSummarize} disabled={loading}>
          {loading ? t('ai.running') : t('ai.summary.button')}
        </button>
      </div>
      <ErrorOrNotConfigured error={error} t={t} />
      {summary && <p className="ai-result">{summary}</p>}
    </section>
  )
}

function CompareSection() {
  const { t, language } = useLanguage()
  const [symbolsRaw, setSymbolsRaw] = useState('AAPL, MSFT')
  const [comparison, setComparison] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function runCompare() {
    setError(null)
    setLoading(true)
    setComparison(null)
    try {
      const symbols = parseSymbols(symbolsRaw)
      if (symbols.length < 2) throw new Error(t('ai.compare.needTwo'))
      const metricsBySymbol = {}
      await Promise.all(
        symbols.map(async (sym) => {
          const [technicals, fundamentals] = await Promise.all([
            api.technicals(sym).catch(() => null),
            api.fundamentals(sym).catch(() => null),
          ])
          metricsBySymbol[sym] = { ...(technicals?.metrics || {}), ...(fundamentals || {}) }
        })
      )
      const result = await api.aiCompare(symbols, metricsBySymbol, language)
      setComparison(result.comparison)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="ai-section">
      <h3>{t('ai.compare.title')}</h3>
      <p className="page-hint">{t('ai.compare.hint')}</p>
      <div className="form-row">
        <input type="text" value={symbolsRaw} onChange={(e) => setSymbolsRaw(e.target.value)} />
        <button onClick={runCompare} disabled={loading}>
          {loading ? t('ai.running') : t('ai.compare.button')}
        </button>
      </div>
      <ErrorOrNotConfigured error={error} t={t} />
      {comparison && <p className="ai-result">{comparison}</p>}
    </section>
  )
}

function StrategySection() {
  const { t, language } = useLanguage()
  const [goal, setGoal] = useState('')
  const [suggestion, setSuggestion] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const [optSymbol, setOptSymbol] = useState('AAPL')
  const [optFormula, setOptFormula] = useState('close > sma_20 AND close > ema_20')
  const [optResult, setOptResult] = useState(null)
  const [optError, setOptError] = useState(null)
  const [optLoading, setOptLoading] = useState(false)

  async function runSuggest() {
    setError(null)
    setLoading(true)
    setSuggestion(null)
    try {
      if (!goal.trim()) throw new Error(t('ai.strategy.enterGoal'))
      const result = await api.aiSuggestStrategy(goal.trim(), language)
      setSuggestion(result.suggestion)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function runOptimize() {
    setOptError(null)
    setOptLoading(true)
    setOptResult(null)
    try {
      const cleanSymbol = optSymbol.trim().toUpperCase()
      if (!cleanSymbol) throw new Error(t('ai.summary.enterSymbol'))
      if (!optFormula.trim()) throw new Error(t('backtest.enterFormula'))
      const backtestResult = await api.backtest({ symbol: cleanSymbol, formula: optFormula.trim() })
      const backtestMetrics = {
        total_return_pct: backtestResult.total_return_pct,
        cagr_pct: backtestResult.cagr_pct,
        max_drawdown_pct: backtestResult.max_drawdown_pct,
        sharpe_ratio: backtestResult.sharpe_ratio,
        win_rate_pct: backtestResult.win_rate_pct,
        profit_factor: backtestResult.profit_factor,
        trade_count: backtestResult.trade_count,
      }
      const result = await api.aiOptimizeStrategy(optFormula.trim(), backtestMetrics, language)
      setOptResult(result.suggestion)
    } catch (err) {
      setOptError(err.message)
    } finally {
      setOptLoading(false)
    }
  }

  return (
    <section className="ai-section">
      <h3>{t('ai.strategy.suggestTitle')}</h3>
      <p className="page-hint">{t('ai.strategy.suggestHint')}</p>
      <div className="custom-formula">
        <label htmlFor="ai-goal">{t('ai.strategy.goalLabel')}</label>
        <input
          id="ai-goal"
          type="text"
          placeholder={t('ai.strategy.goalPlaceholder')}
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
        />
      </div>
      <div className="form-row">
        <button onClick={runSuggest} disabled={loading}>
          {loading ? t('ai.running') : t('ai.strategy.suggestButton')}
        </button>
      </div>
      <ErrorOrNotConfigured error={error} t={t} />
      {suggestion && <p className="ai-result">{suggestion}</p>}

      <h3>{t('ai.strategy.optimizeTitle')}</h3>
      <p className="page-hint">{t('ai.strategy.optimizeHint')}</p>
      <div className="form-row">
        <label>
          {t('common.symbol')}
          <input type="text" value={optSymbol} onChange={(e) => setOptSymbol(e.target.value)} />
        </label>
      </div>
      <div className="custom-formula">
        <label htmlFor="ai-opt-formula">{t('backtest.formula')}</label>
        <input
          id="ai-opt-formula"
          type="text"
          value={optFormula}
          onChange={(e) => setOptFormula(e.target.value)}
        />
      </div>
      <div className="form-row">
        <button onClick={runOptimize} disabled={optLoading}>
          {optLoading ? t('ai.running') : t('ai.strategy.optimizeButton')}
        </button>
      </div>
      <ErrorOrNotConfigured error={optError} t={t} />
      {optResult && <p className="ai-result">{optResult}</p>}
    </section>
  )
}

export default function AiPage() {
  const { t } = useLanguage()

  return (
    <section className="page">
      <h2>{t('ai.title')}</h2>
      <p className="page-hint">{t('ai.hint')}</p>

      <SettingsSection />
      <ExplainDebugSection />
      <SummarySection />
      <CompareSection />
      <StrategySection />
    </section>
  )
}
