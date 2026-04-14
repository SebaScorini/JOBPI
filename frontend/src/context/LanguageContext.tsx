import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { AIResponseLanguage, UILanguage } from '../types';
import { getCachedTranslations, loadTranslations, toAIResponseLanguage, translate } from '../i18n/translations';
import type { TranslationNode } from '../i18n/types';
import { RouteFallback } from '../components/RouteFallback';

interface LanguageContextValue {
  language: UILanguage;
  aiLanguage: AIResponseLanguage;
  isReady: boolean;
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
  const [dictionary, setDictionary] = useState<TranslationNode | null>(() => getCachedTranslations(getInitialLanguage()));
  const [isReady, setIsReady] = useState<boolean>(() => getCachedTranslations(getInitialLanguage()) !== null);

  useEffect(() => {
    let cancelled = false;

    loadTranslations(language)
      .then((loadedDictionary) => {
        if (cancelled) {
          return;
        }

        setDictionary(loadedDictionary);
        setIsReady(true);
      })
      .catch(() => {
        if (!cancelled) {
          setIsReady(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [language]);

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
      isReady,
      setLanguage: setLanguageState,
      t: (key, params) => translate(dictionary, key, params),
    }),
    [dictionary, isReady, language],
  );

  return (
    <LanguageContext.Provider value={value}>
      {isReady ? children : <RouteFallback variant="public" />}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used inside LanguageProvider');
  }
  return context;
}
