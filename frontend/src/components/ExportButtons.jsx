import { buildReportHtml, downloadHtml, printReport } from '../utils/report.js'
import { useLanguage } from '../i18n/LanguageContext.jsx'

function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
}

export default function ExportButtons({ spec }) {
  const { t } = useLanguage()

  function handleExportHtml() {
    const html = buildReportHtml(spec)
    const filename = `${slugify(spec.title)}-${new Date().toISOString().slice(0, 10)}`
    downloadHtml(filename, html)
  }

  function handleExportPdf() {
    const html = buildReportHtml(spec)
    printReport(html)
  }

  return (
    <div className="export-buttons">
      <button type="button" onClick={handleExportHtml}>
        {t('export.html')}
      </button>
      <button type="button" onClick={handleExportPdf}>
        {t('export.pdf')}
      </button>
    </div>
  )
}
