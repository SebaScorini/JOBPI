import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { AIResponseLanguage, UILanguage, toAIResponseLanguage, translate } from '../i18n/translations';

interface LanguageContextValue {
  language: UILanguage;
  aiLanguage: AIResponseLanguage;
  setLanguage: (language: UILanguage) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const LANGUAGE_STORAGE_KEY = 'jobpi_language';
const LEGACY_LANGUAGE_STORAGE_KEY = 'jobpi_ai_language';

const LanguageContext = createContext<LanguageContextValue | null>(null);

function getInitialLanguage(): UILanguage {
  if (typeof window === 'undefined') {
    return 'en';
  }

  const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (stored === 'en' || stored === 'es') {
    return stored;
  }

  const legacyStored = window.localStorage.getItem(LEGACY_LANGUAGE_STORAGE_KEY);
  if (legacyStored === 'spanish') {
    return 'es';
  }

  return 'en';
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<UILanguage>(getInitialLanguage);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    window.localStorage.setItem(LEGACY_LANGUAGE_STORAGE_KEY, toAIResponseLanguage(language));
    document.documentElement.lang = language;
  }, [language]);

  const value = useMemo<LanguageContextValue>(
    () => ({
      language,
      aiLanguage: toAIResponseLanguage(language),
      setLanguage: setLanguageState,
      t: (key, params) => translate(language, key, params),
    }),
    [language],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used inside LanguageProvider');
  }
  return context;
}
