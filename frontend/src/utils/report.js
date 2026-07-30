// Shared export template. Every page builds a plain-data "report spec" and
// hands it to buildReportHtml(); the same template renders meta rows, metric
// cards, and data tables consistently across Screener/Ranking/Backtest/
// Fundamentals/Valuation. Two consumers use the output: downloadHtml() for a
// standalone .html file, and printReport() for browser print-to-PDF.

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function formatCell(value, { yes = 'yes', no = 'no' } = {}) {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'number') {
    return Number.isInteger(value) ? String(value) : value.toFixed(4)
  }
  if (typeof value === 'boolean') return value ? yes : no
  return String(value)
}

function renderMeta(meta) {
  if (!meta || meta.length === 0) return ''
  const rows = meta
    .filter((item) => item.value !== null && item.value !== undefined && item.value !== '')
    .map(
      (item) =>
        `<tr><th>${escapeHtml(item.label)}</th><td>${escapeHtml(item.value)}</td></tr>`
    )
    .join('')
  return `<table class="meta-table">${rows}</table>`
}

function renderCards(cards, labels) {
  if (!cards || cards.length === 0) return ''
  const items = cards
    .map(
      (card) =>
        `<div class="card"><div class="card-label">${escapeHtml(card.label)}</div><div class="card-value">${escapeHtml(
          formatCell(card.value, labels)
        )}</div></div>`
    )
    .join('')
  return `<div class="cards">${items}</div>`
}

function renderTable(table, labels) {
  if (!table || !table.rows || table.rows.length === 0) {
    return `<p class="empty">${escapeHtml(table?.emptyMessage || 'No data.')}</p>`
  }
  const head = table.columns.map((col) => `<th>${escapeHtml(col.label)}</th>`).join('')
  const body = table.rows
    .map((row) => {
      const cells = table.columns
        .map((col) => {
          const raw = col.get ? col.get(row) : row[col.key]
          return `<td>${escapeHtml(formatCell(raw, labels))}</td>`
        })
        .join('')
      return `<tr>${cells}</tr>`
    })
    .join('')
  return `<table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`
}

function renderSection(section, labels) {
  const heading = section.heading ? `<h2>${escapeHtml(section.heading)}</h2>` : ''
  if (section.type === 'cards') {
    return `<section>${heading}${renderCards(section.cards, labels)}</section>`
  }
  if (section.type === 'table') {
    return `<section>${heading}${renderTable(section.table, labels)}</section>`
  }
  return ''
}

/**
 * spec = {
 *   title, subtitle, generatedAtLabel, generatedAt,
 *   meta: [{ label, value }],
 *   sections: [{ type: 'cards' | 'table', heading, cards, table: { columns, rows, emptyMessage } }],
 *   footerNote,
 *   labels: { yes, no },
 * }
 */
export function buildReportHtml(spec) {
  const { title, subtitle, generatedAtLabel, generatedAt, meta, sections, footerNote, labels } = spec

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>${escapeHtml(title)}</title>
<style>
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, 'Segoe UI', Roboto, sans-serif;
    color: #1a1a1a;
    margin: 0;
    padding: 32px;
    background: #fff;
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    border-bottom: 2px solid #1a1a1a;
    padding-bottom: 12px;
    margin-bottom: 20px;
  }
  header .brand { font-size: 22px; font-weight: 700; letter-spacing: 1px; }
  header .generated { font-size: 12px; color: #555; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  h2 { font-size: 15px; margin: 24px 0 8px; border-left: 4px solid #aa3bff; padding-left: 8px; }
  .subtitle { font-size: 13px; color: #555; margin-bottom: 16px; }
  table { border-collapse: collapse; width: 100%; font-size: 12px; }
  .meta-table { margin-bottom: 16px; }
  .meta-table th { text-align: left; color: #555; font-weight: 600; padding: 3px 12px 3px 0; white-space: nowrap; }
  .meta-table td { padding: 3px 0; }
  .data-table th, .data-table td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; }
  .data-table th { background: #f4f3ec; }
  .cards { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 8px; }
  .card { border: 1px solid #ddd; border-radius: 6px; padding: 8px 14px; min-width: 130px; }
  .card-label { font-size: 11px; color: #555; }
  .card-value { font-size: 16px; font-weight: 700; }
  .empty { color: #777; font-size: 13px; }
  footer { margin-top: 28px; padding-top: 12px; border-top: 1px solid #ddd; font-size: 11px; color: #777; }
  @media print {
    body { padding: 12mm; }
    section { page-break-inside: avoid; }
  }
</style>
</head>
<body>
  <header>
    <div>
      <div class="brand">GIRP</div>
    </div>
    <div class="generated">${escapeHtml(generatedAtLabel)}: ${escapeHtml(generatedAt)}</div>
  </header>
  <h1>${escapeHtml(title)}</h1>
  ${subtitle ? `<div class="subtitle">${escapeHtml(subtitle)}</div>` : ''}
  ${renderMeta(meta)}
  ${(sections || []).map((section) => renderSection(section, labels)).join('')}
  ${footerNote ? `<footer>${escapeHtml(footerNote)}</footer>` : ''}
</body>
</html>`
}

export function downloadHtml(filename, html) {
  const blob = new Blob([html], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename.endsWith('.html') ? filename : `${filename}.html`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function printReport(html) {
  const iframe = document.createElement('iframe')
  iframe.style.position = 'fixed'
  iframe.style.right = '0'
  iframe.style.bottom = '0'
  iframe.style.width = '0'
  iframe.style.height = '0'
  iframe.style.border = '0'
  document.body.appendChild(iframe)

  const cleanup = () => {
    setTimeout(() => iframe.remove(), 1000)
  }

  iframe.onload = () => {
    try {
      iframe.contentWindow.focus()
      iframe.contentWindow.print()
    } finally {
      cleanup()
    }
  }
  iframe.srcdoc = html
}
