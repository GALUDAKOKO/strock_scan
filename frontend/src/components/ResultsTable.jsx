import { useMemo, useState } from 'react'
import { useLanguage } from '../i18n/LanguageContext.jsx'

function formatValue(value, t) {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'number') {
    return Number.isInteger(value) ? value.toString() : value.toFixed(4)
  }
  if (typeof value === 'boolean') return value ? t('common.yes') : t('common.no')
  return String(value)
}

function getRawValue(column, row) {
  return column.get ? column.get(row) : row[column.key]
}

function compareValues(a, b) {
  const aMissing = a === null || a === undefined || a === '-'
  const bMissing = b === null || b === undefined || b === '-'
  if (aMissing && bMissing) return 0
  if (aMissing) return 1 // missing values always sort to the bottom, regardless of direction
  if (bMissing) return -1

  if (typeof a === 'number' && typeof b === 'number') return a - b
  const aNum = Number(a)
  const bNum = Number(b)
  if (!Number.isNaN(aNum) && !Number.isNaN(bNum) && a !== '' && b !== '') return aNum - bNum
  return String(a).localeCompare(String(b))
}

export default function ResultsTable({ columns, rows, emptyMessage, sortable = false }) {
  const { t } = useLanguage()
  const [sortKey, setSortKey] = useState(null)
  const [sortDirection, setSortDirection] = useState('desc')

  const sortedRows = useMemo(() => {
    if (!sortable || !sortKey || !rows) return rows
    const column = columns.find((c) => c.key === sortKey)
    if (!column) return rows
    const withIndex = rows.map((row, index) => ({ row, index }))
    withIndex.sort((a, b) => {
      const cmp = compareValues(getRawValue(column, a.row), getRawValue(column, b.row))
      if (cmp !== 0) return sortDirection === 'desc' ? -cmp : cmp
      return a.index - b.index // stable sort
    })
    return withIndex.map((entry) => entry.row)
  }, [sortable, sortKey, sortDirection, rows, columns])

  if (!rows || rows.length === 0) {
    return <p className="empty-message">{emptyMessage || t('common.noResults')}</p>
  }

  function handleHeaderClick(column) {
    if (!sortable) return
    if (sortKey === column.key) {
      setSortDirection((prev) => (prev === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortKey(column.key)
      setSortDirection('desc')
    }
  }

  return (
    <div className="table-wrapper">
      <table className="results-table">
        <thead>
          <tr>
            {columns.map((column) => {
              const isActive = sortable && sortKey === column.key
              return (
                <th
                  key={column.key}
                  className={sortable ? 'sortable' : undefined}
                  onClick={() => handleHeaderClick(column)}
                >
                  {column.label}
                  {isActive && <span className="sort-arrow">{sortDirection === 'desc' ? ' ▼' : ' ▲'}</span>}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {(sortedRows || rows).map((row, index) => (
            <tr key={row.symbol ? `${row.symbol}-${index}` : index}>
              {columns.map((column) => (
                <td key={column.key}>{formatValue(getRawValue(column, row), t)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
