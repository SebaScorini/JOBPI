import { useLanguage } from '../context/LanguageContext';

interface LanguageSelectorProps {
  className?: string;
}

export function LanguageSelector({ className }: LanguageSelectorProps) {
  const { language, setLanguage, t } = useLanguage();

  return (
    <select
      value={language}
      onChange={(event) => setLanguage(event.target.value as 'en' | 'es')}
      className={className}
      aria-label={t('nav.aiResponseLanguage')}
    >
      <option value="en">{t('common.english')}</option>
      <option value="es">{t('common.spanish')}</option>
    </select>
  );
}
