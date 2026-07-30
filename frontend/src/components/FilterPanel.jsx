import { ASSET_TYPES, SECTORS, TECHNICAL_FILTERS, FUNDAMENTAL_FILTERS } from '../filters.js'
import { useLanguage } from '../i18n/LanguageContext.jsx'

function FilterGroup({ title, filters, selected, onToggle, t }) {
  return (
    <fieldset className="filter-group">
      <legend>{title}</legend>
      <div className="filter-checkboxes">
        {filters.map((filter) => (
          <label key={filter.id} className="filter-checkbox">
            <input
              type="checkbox"
              checked={selected.has(filter.id)}
              onChange={() => onToggle(filter.id)}
            />
            <span>{t(`filters.${filter.id}`)}</span>
          </label>
        ))}
      </div>
    </fieldset>
  )
}

export default function FilterPanel({
  selected,
  onToggle,
  customFormula,
  onCustomFormulaChange,
  includeFundamentals,
  onIncludeFundamentalsChange,
  sector = '',
  onSectorChange,
  assetType = '',
  onAssetTypeChange,
}) {
  const { t } = useLanguage()

  return (
    <div className="filter-panel">
      <FilterGroup
        title={t('common.filterGroupTechnical')}
        filters={TECHNICAL_FILTERS}
        selected={selected}
        onToggle={onToggle}
        t={t}
      />
      <FilterGroup
        title={t('common.filterGroupFundamental')}
        filters={FUNDAMENTAL_FILTERS}
        selected={selected}
        onToggle={onToggle}
        t={t}
      />
      {onSectorChange && onAssetTypeChange && (
        <fieldset className="filter-group">
          <legend>{t('common.filterGroupClassification')}</legend>
          <div className="form-row">
            <label>
              {t('common.sectorLabel')}
              <select value={sector} onChange={(e) => onSectorChange(e.target.value)}>
                <option value="">{t('common.anySector')}</option>
                {SECTORS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t('common.assetTypeLabel')}
              <select value={assetType} onChange={(e) => onAssetTypeChange(e.target.value)}>
                <option value="">{t('common.anyAssetType')}</option>
                {ASSET_TYPES.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="page-hint">{t('common.classificationHint')}</p>
        </fieldset>
      )}
      <label className="filter-checkbox include-fundamentals">
        <input
          type="checkbox"
          checked={includeFundamentals}
          onChange={(event) => onIncludeFundamentalsChange(event.target.checked)}
        />
        <span>{t('common.includeFundamentals')}</span>
      </label>
      <div className="custom-formula">
        <label htmlFor="custom-formula-input">{t('common.customFormulaLabel')}</label>
        <input
          id="custom-formula-input"
          type="text"
          placeholder={t('common.customFormulaPlaceholder')}
          value={customFormula}
          onChange={(event) => onCustomFormulaChange(event.target.value)}
        />
      </div>
    </div>
  )
}
