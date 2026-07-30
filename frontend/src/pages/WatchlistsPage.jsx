import { useEffect, useState } from 'react'
import * as XLSX from 'xlsx'
import { api, parseSymbols } from '../api.js'
import SymbolsInput from '../components/SymbolsInput.jsx'
import { useLanguage } from '../i18n/LanguageContext.jsx'

const SPREADSHEET_EXTENSIONS = ['.xlsx', '.xls']
const HEADER_RE = /^(symbol|ticker|stock|code)s?$/i

function isHeaderCell(value, collectedSoFar) {
  return collectedSoFar === 0 && HEADER_RE.test(value)
}

function extractSymbolsFromWorkbook(arrayBuffer) {
  const workbook = XLSX.read(arrayBuffer, { type: 'array' })
  const firstSheetName = workbook.SheetNames[0]
  const sheet = workbook.Sheets[firstSheetName]
  const rows = XLSX.utils.sheet_to_json(sheet, { header: 1 })

  const tokens = []
  for (const row of rows) {
    // Only the first column is read -- extra columns (company name, sector,
    // notes, ...) are ignored rather than accidentally tokenized.
    const cell = row?.[0]
    if (cell === undefined || cell === null) continue
    const value = String(cell).trim()
    if (!value || isHeaderCell(value, tokens.length)) continue
    tokens.push(value)
  }
  return tokens.join(', ')
}

// A .csv file may have extra columns (Name, Sector, ...); only the first
// column of each line is treated as the symbol. Plain .txt files have no
// column structure, so those are left as raw text for parseSymbols() to
// tokenize on comma/whitespace/newline.
function extractSymbolsFromCsvText(text) {
  const tokens = []
  for (const line of text.split(/\r?\n/)) {
    if (!line.trim()) continue
    const firstField = line.split(',')[0].trim().replace(/^"(.*)"$/, '$1').trim()
    if (!firstField || isHeaderCell(firstField, tokens.length)) continue
    tokens.push(firstField)
  }
  return tokens.join(', ')
}

export default function WatchlistsPage({ active = true }) {
  const { t } = useLanguage()
  const [watchlists, setWatchlists] = useState([])
  const [name, setName] = useState('')
  const [symbolsRaw, setSymbolsRaw] = useState('')
  const [loading, setLoading] = useState(false)
  const [listLoading, setListLoading] = useState(true)
  const [error, setError] = useState(null)
  const [message, setMessage] = useState(null)

  async function refresh() {
    setListLoading(true)
    try {
      const response = await api.listWatchlists()
      setWatchlists(response.watchlists)
    } catch (err) {
      setError(err.message)
    } finally {
      setListLoading(false)
    }
  }

  useEffect(() => {
    if (active) refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active])

  async function handleSave() {
    setError(null)
    setMessage(null)
    setLoading(true)
    try {
      if (!name.trim()) throw new Error(t('watchlists.enterName'))
      const symbols = parseSymbols(symbolsRaw)
      if (symbols.length === 0) throw new Error(t('watchlists.enterSymbols'))
      await api.saveWatchlist(name.trim(), symbols)
      setMessage(t('watchlists.saved', name.trim(), symbols.length))
      await refresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleEdit(watchlist) {
    setName(watchlist.name)
    setSymbolsRaw(watchlist.symbols.join(', '))
    setMessage(null)
    setError(null)
  }

  async function handleDelete(watchlistName) {
    if (!window.confirm(t('watchlists.confirmDelete', watchlistName))) return
    setError(null)
    try {
      await api.deleteWatchlist(watchlistName)
      await refresh()
      if (name === watchlistName) {
        setName('')
        setSymbolsRaw('')
      }
    } catch (err) {
      setError(err.message)
    }
  }

  function handleFile(event) {
    const file = event.target.files?.[0]
    if (!file) return
    const lowerName = file.name.toLowerCase()
    const isSpreadsheet = SPREADSHEET_EXTENSIONS.some((ext) => lowerName.endsWith(ext))
    const isCsv = lowerName.endsWith('.csv')
    const reader = new FileReader()

    reader.onload = () => {
      try {
        let text
        if (isSpreadsheet) {
          text = extractSymbolsFromWorkbook(reader.result)
        } else if (isCsv) {
          text = extractSymbolsFromCsvText(String(reader.result || ''))
        } else {
          text = String(reader.result || '')
        }
        setSymbolsRaw((prev) => (prev.trim() ? `${prev}, ${text}` : text))
      } catch {
        setError(t('watchlists.importError'))
      }
    }

    if (isSpreadsheet) {
      reader.readAsArrayBuffer(file)
    } else {
      reader.readAsText(file)
    }
    event.target.value = ''
  }

  return (
    <section className="page">
      <h2>{t('watchlists.title')}</h2>
      <p className="page-hint">{t('watchlists.hint')}</p>

      <div className="form-row">
        <label>
          {t('watchlists.nameLabel')}
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder={t('watchlists.namePlaceholder')} />
        </label>
      </div>

      <SymbolsInput value={symbolsRaw} onChange={setSymbolsRaw} />

      <div className="form-row">
        <label className="file-import-label">
          {t('watchlists.importFile')}
          <input type="file" accept=".csv,.txt,.xlsx,.xls" onChange={handleFile} />
        </label>
        <button onClick={handleSave} disabled={loading}>
          {loading ? t('watchlists.saving') : t('watchlists.save')}
        </button>
      </div>

      {error && <p className="error-message">{error}</p>}
      {message && <p className="result-summary">{message}</p>}

      <h2>{t('watchlists.savedTitle')}</h2>
      {listLoading ? (
        <p className="page-hint">{t('common.loading')}</p>
      ) : watchlists.length === 0 ? (
        <p className="empty-message">{t('watchlists.empty')}</p>
      ) : (
        <div className="table-wrapper">
          <table className="results-table">
            <thead>
              <tr>
                <th>{t('watchlists.columns.name')}</th>
                <th>{t('watchlists.columns.count')}</th>
                <th>{t('watchlists.columns.updatedAt')}</th>
                <th>{t('watchlists.columns.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {watchlists.map((watchlist) => (
                <tr key={watchlist.name}>
                  <td>{watchlist.name}</td>
                  <td>{watchlist.count}</td>
                  <td>{watchlist.updated_at ? new Date(watchlist.updated_at).toLocaleString() : '-'}</td>
                  <td className="row-actions">
                    <button type="button" onClick={() => handleEdit(watchlist)}>
                      {t('watchlists.edit')}
                    </button>
                    <button type="button" className="danger" onClick={() => handleDelete(watchlist.name)}>
                      {t('watchlists.delete')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
