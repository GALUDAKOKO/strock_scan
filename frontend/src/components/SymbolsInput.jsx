import { useLanguage } from '../i18n/LanguageContext.jsx'

export default function SymbolsInput({ value, onChange }) {
  const { t } = useLanguage()

  return (
    <div className="symbols-input">
      <label htmlFor="symbols-input-field">{t('common.symbolsLabel')}</label>
      <textarea
        id="symbols-input-field"
        rows={2}
        placeholder={t('common.symbolsPlaceholder')}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  )
}
