const BASE_URL = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const isJson = response.headers.get('content-type')?.includes('application/json')
  const body = isJson ? await response.json() : await response.text()
  if (!response.ok) {
    const detail = isJson ? body.detail || JSON.stringify(body) : body
    throw new Error(detail || `Request failed with status ${response.status}`)
  }
  return body
}

export function parseSymbols(raw) {
  const tokens = raw
    .split(/[\s,;]+/)
    .map((symbol) => symbol.trim().toUpperCase())
    .filter(Boolean)
  return [...new Set(tokens)]
}

export const api = {
  baseUrl: BASE_URL,

  health: () => request('/health'),

  assetInfo: (symbol, refresh = false) =>
    request(`/assets/${encodeURIComponent(symbol)}?refresh=${refresh}`),

  history: (symbol, params = {}) => {
    const query = new URLSearchParams(params).toString()
    return request(`/assets/${encodeURIComponent(symbol)}/history${query ? `?${query}` : ''}`)
  },

  fundamentals: (symbol, refresh = false) =>
    request(`/assets/${encodeURIComponent(symbol)}/fundamentals?refresh=${refresh}`),

  technicals: (symbol, refresh = false) =>
    request(`/assets/${encodeURIComponent(symbol)}/technicals?refresh=${refresh}`),

  screen: (payload) =>
    request('/screen', { method: 'POST', body: JSON.stringify(payload) }),

  rank: (payload) =>
    request('/rank', { method: 'POST', body: JSON.stringify(payload) }),

  backtest: (payload) =>
    request('/backtest', { method: 'POST', body: JSON.stringify(payload) }),

  valuation: (payload) =>
    request('/valuation', { method: 'POST', body: JSON.stringify(payload) }),

  listWatchlists: () => request('/watchlists'),

  getWatchlist: (name) => request(`/watchlists/${encodeURIComponent(name)}`),

  saveWatchlist: (name, symbols) =>
    request(`/watchlists/${encodeURIComponent(name)}`, {
      method: 'PUT',
      body: JSON.stringify({ symbols }),
    }),

  deleteWatchlist: (name) =>
    request(`/watchlists/${encodeURIComponent(name)}`, { method: 'DELETE' }),

  aiExplainFormula: (formula, lang) =>
    request('/ai/explain-formula', { method: 'POST', body: JSON.stringify({ formula, lang }) }),

  aiDebugFormula: (formula, lang) =>
    request('/ai/debug-formula', { method: 'POST', body: JSON.stringify({ formula, lang }) }),

  aiSummarize: (symbol, metrics, lang) =>
    request('/ai/summarize', { method: 'POST', body: JSON.stringify({ symbol, metrics, lang }) }),

  aiCompare: (symbols, metricsBySymbol, lang) =>
    request('/ai/compare', {
      method: 'POST',
      body: JSON.stringify({ symbols, metrics_by_symbol: metricsBySymbol, lang }),
    }),

  aiSuggestStrategy: (goal, lang) =>
    request('/ai/suggest-strategy', { method: 'POST', body: JSON.stringify({ goal, lang }) }),

  aiOptimizeStrategy: (formula, backtestMetrics, lang) =>
    request('/ai/optimize-strategy', {
      method: 'POST',
      body: JSON.stringify({ formula, backtest_metrics: backtestMetrics, lang }),
    }),

  getAiSettings: () => request('/ai/settings'),

  saveAiSettings: (provider, apiKey, model) =>
    request('/ai/settings', {
      method: 'POST',
      body: JSON.stringify({ provider, api_key: apiKey, model: model || undefined }),
    }),

  deleteAiSettings: () => request('/ai/settings', { method: 'DELETE' }),
}
