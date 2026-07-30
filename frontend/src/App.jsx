import { useState } from 'react'
import ScreenerPage from './pages/ScreenerPage.jsx'
import RankingPage from './pages/RankingPage.jsx'
import BacktestPage from './pages/BacktestPage.jsx'
import FundamentalsPage from './pages/FundamentalsPage.jsx'
import ValuationPage from './pages/ValuationPage.jsx'
import AssetDetailPage from './pages/AssetDetailPage.jsx'
import WatchlistsPage from './pages/WatchlistsPage.jsx'
import AiPage from './pages/AiPage.jsx'
import { api } from './api.js'
import { useLanguage } from './i18n/LanguageContext.jsx'
import { LANGUAGES } from './i18n/translations.js'
import './App.css'

const TABS = [
  { id: 'screener', navKey: 'nav.screener', component: ScreenerPage },
  { id: 'ranking', navKey: 'nav.ranking', component: RankingPage },
  { id: 'backtest', navKey: 'nav.backtest', component: BacktestPage },
  { id: 'fundamentals', navKey: 'nav.fundamentals', component: FundamentalsPage },
  { id: 'valuation', navKey: 'nav.valuation', component: ValuationPage },
  { id: 'assetDetail', navKey: 'nav.assetDetail', component: AssetDetailPage },
  { id: 'watchlists', navKey: 'nav.watchlists', component: WatchlistsPage },
  { id: 'ai', navKey: 'nav.ai', component: AiPage },
]

function App() {
  const [activeTab, setActiveTab] = useState('screener')
  const { language, setLanguage, t } = useLanguage()

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>{t('app.title')}</h1>
        <div className="header-right">
          <span className="api-base">{api.baseUrl}</span>
          <div className="language-switch" role="group" aria-label="Language">
            {LANGUAGES.map((option) => (
              <button
                key={option.code}
                type="button"
                className={option.code === language ? 'lang-button active' : 'lang-button'}
                onClick={() => setLanguage(option.code)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </header>
      <nav className="app-nav">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={tab.id === activeTab ? 'nav-button active' : 'nav-button'}
            onClick={() => setActiveTab(tab.id)}
          >
            {t(tab.navKey)}
          </button>
        ))}
      </nav>
      <main className="app-main">
        {TABS.map((tab) => {
          const Component = tab.component
          const isActive = tab.id === activeTab
          return (
            <div key={tab.id} className={isActive ? 'tab-panel' : 'tab-panel hidden'}>
              <Component active={isActive} />
            </div>
          )
        })}
      </main>
    </div>
  )
}

export default App
