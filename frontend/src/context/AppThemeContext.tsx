import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

export type ThemeMode = 'light' | 'dark' | 'system';

const THEME_STORAGE_KEY = 'jobpi_theme_mode';

interface AppThemeContextValue {
  mode: ThemeMode;
  resolvedTheme: 'light' | 'dark';
  setThemeMode: (mode: ThemeMode) => void;
  toggleDarkMode: () => void;
}

const AppThemeContext = createContext<AppThemeContextValue | undefined>(undefined);

function getStoredThemeMode(): ThemeMode {
  if (typeof window === 'undefined') {
    return 'system';
  }

  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === 'light' || stored === 'dark' || stored === 'system') {
    return stored;
  }

  return 'system';
}

function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') {
    return 'light';
  }

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyResolvedTheme(theme: 'light' | 'dark') {
  const root = document.documentElement;
  root.classList.add('theme-transition');
  root.classList.toggle('dark', theme === 'dark');
  window.setTimeout(() => root.classList.remove('theme-transition'), 350);
}

export function AppThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(() => getStoredThemeMode());
  const [systemTheme, setSystemTheme] = useState<'light' | 'dark'>(() => getSystemTheme());

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const listener = (event: MediaQueryListEvent) => {
      setSystemTheme(event.matches ? 'dark' : 'light');
    };

    setSystemTheme(mediaQuery.matches ? 'dark' : 'light');
    mediaQuery.addEventListener('change', listener);

    return () => {
      mediaQuery.removeEventListener('change', listener);
    };
  }, []);

  const resolvedTheme = mode === 'system' ? systemTheme : mode;

  useEffect(() => {
    window.localStorage.setItem(THEME_STORAGE_KEY, mode);
  }, [mode]);

  useEffect(() => {
    applyResolvedTheme(resolvedTheme);
  }, [resolvedTheme]);

  const value = useMemo<AppThemeContextValue>(
    () => ({
      mode,
      resolvedTheme,
      setThemeMode: setMode,
      toggleDarkMode: () => {
        setMode((currentMode) => {
          const currentResolvedTheme = currentMode === 'system' ? getSystemTheme() : currentMode;
          return currentResolvedTheme === 'dark' ? 'light' : 'dark';
        });
      },
    }),
    [mode, resolvedTheme],
  );

  return <AppThemeContext.Provider value={value}>{children}</AppThemeContext.Provider>;
}

export function useAppTheme() {
  const context = useContext(AppThemeContext);
  if (!context) {
    throw new Error('useAppTheme must be used within an AppThemeProvider');
  }

  return context;
}

export const themeStorage = {
  key: THEME_STORAGE_KEY,
};
