import { useState, useEffect } from 'react';

type FontSize = '85%' | '90%' | '100%' | '110%';
type FontFamily = 'DM Sans' | 'Inter' | 'Outfit' | 'Plus Jakarta Sans';

export function useAppearance() {
  const [fontSize, setFontSize] = useState<FontSize>(() => {
    return (localStorage.getItem('jobpi_font_size') as FontSize) || '90%';
  });

  const [fontFamily, setFontFamily] = useState<FontFamily>(() => {
    return (localStorage.getItem('jobpi_font_family') as FontFamily) || 'DM Sans';
  });

  useEffect(() => {
    // Apply font size
    document.documentElement.style.fontSize = fontSize;
    localStorage.setItem('jobpi_font_size', fontSize);
  }, [fontSize]);

  useEffect(() => {
    // Apply font family
    // The default in Tailwind config might be overriding this if we just set style.fontFamily
    // So we can set a CSS variable and update index.css to use it, OR just set style.fontFamily directly
    // Let's set a CSS variable that we will use in index.css
    document.documentElement.style.setProperty('--user-font-family', `"${fontFamily}", sans-serif`);
    localStorage.setItem('jobpi_font_family', fontFamily);
  }, [fontFamily]);

  return {
    fontSize,
    setFontSize,
    fontFamily,
    setFontFamily,
  };
}
