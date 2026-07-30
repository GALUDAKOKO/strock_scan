import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLanguage } from '../i18n/LanguageContext.jsx'

export default function WatchlistPicker({ onLoad, active = true }) {
  const { t } = useLanguage()
  const [watchlists, setWatchlists] = useState([])
  const [selected, setSelected] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // Pages stay mounted after their tab loses focus, so re-fetch every time
    // this tab becomes active again -- otherwise a watchlist saved on
    // another tab would never show up here without a full page reload.
    if (!active) return
    let cancelled = false
    api
      .listWatchlists()
      .then((response) => {
        if (cancelled) return
        setWatchlists(response.watchlists)
        setSelected((prev) =>
          response.watchlists.some((watchlist) => watchlist.name === prev)
            ? prev
            : response.watchlists[0]?.name || ''
        )
      })
      .catch(() => {
        if (!cancelled) setWatchlists([])
      })
    return () => {
      cancelled = true
    }
  }, [active])

  async function handleLoad() {
    if (!selected) return
    setLoading(true)
    try {
      const watchlist = await api.getWatchlist(selected)
      onLoad(watchlist.symbols.join(', '))
    } catch {
      // Silently ignore -- the symbols box just won't update.
    } finally {
      setLoading(false)
    }
  }

  if (watchlists.length === 0) {
    return null
  }

  return (
    <div className="watchlist-picker">
      <label>
        {t('watchlists.pickerLabel')}
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          {watchlists.map((watchlist) => (
            <option key={watchlist.name} value={watchlist.name}>
              {watchlist.name} ({watchlist.count})
            </option>
          ))}
        </select>
      </label>
      <button type="button" onClick={handleLoad} disabled={loading}>
        {t('watchlists.loadButton')}
      </button>
    </div>
  )
}
