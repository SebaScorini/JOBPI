import type { AIResponseLanguage, UILanguage } from '../types';
import type { TranslationNode, TranslationValue } from './types';

const localeLoaders = {
  en: () => import('./locales/en'),
  es: () => import('./locales/es'),
} satisfies Record<UILanguage, () => Promise<{ default: TranslationNode }>>;

const cache = new Map<UILanguage, TranslationNode>();
const inFlight = new Map<UILanguage, Promise<TranslationNode>>();

export async function loadTranslations(language: UILanguage): Promise<TranslationNode> {
  const cached = cache.get(language);
  if (cached) {
    return cached;
  }

  const pending = inFlight.get(language);
  if (pending) {
    return pending;
  }

  const request = localeLoaders[language]()
    .then((module) => {
      cache.set(language, module.default);
      inFlight.delete(language);
      return module.default;
    })
    .catch((error) => {
      inFlight.delete(language);
      throw error;
    });

  inFlight.set(language, request);
  return request;
}

export function getCachedTranslations(language: UILanguage): TranslationNode | null {
  return cache.get(language) ?? null;
}

function getValue(source: TranslationNode, path: string): TranslationValue | undefined {
  return path.split('.').reduce<TranslationValue | undefined>((current, part) => {
    if (!current || typeof current === 'string') {
      return undefined;
    }

    return current[part];
  }, source);
}

export function translate(
  dictionary: TranslationNode | null,
  key: string,
  params?: Record<string, string | number>,
): string {
  const selected = dictionary ? getValue(dictionary, key) : undefined;
  const template = typeof selected === 'string' ? selected : key;

  if (!params) {
    return template;
  }

  return Object.entries(params).reduce(
    (result, [paramKey, value]) => result.split(`{${paramKey}}`).join(String(value)),
    template,
  );
}

export function toAIResponseLanguage(language: UILanguage): AIResponseLanguage {
  return language === 'es' ? 'spanish' : 'english';
}
