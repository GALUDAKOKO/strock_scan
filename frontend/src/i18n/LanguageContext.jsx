import { createContext, useContext, useMemo, useState } from 'react'
import { translations } from './translations.js'

const STORAGE_KEY = 'girp-language'
const DEFAULT_LANGUAGE = 'en'

const LanguageContext = createContext(null)

function detectInitialLanguage() {
  if (typeof window === 'undefined') return DEFAULT_LANGUAGE
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored === 'en' || stored === 'th') return stored
  } catch {
    // localStorage unavailable (e.g. private mode) -- fall back to default.
  }
  return DEFAULT_LANGUAGE
}

function getByPath(source, path) {
  return path.split('.').reduce((acc, key) => (acc == null ? acc : acc[key]), source)
}

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(detectInitialLanguage)

  function setLanguage(next) {
    setLanguageState(next)
    try {
      window.localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Ignore write failures; language just won't persist across reloads.
    }
  }

  const value = useMemo(() => {
    const dictionary = translations[language] || translations[DEFAULT_LANGUAGE]
    const fallback = translations[DEFAULT_LANGUAGE]

    function t(path, ...args) {
      const entry = getByPath(dictionary, path) ?? getByPath(fallback, path)
      if (typeof entry === 'function') return entry(...args)
      return entry ?? path
    }

    return { language, setLanguage, t }
  }, [language])

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider')
  }
  return context
}
