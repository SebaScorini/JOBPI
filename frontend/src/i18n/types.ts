import type { UILanguage } from '../types';

export interface TranslationNode {
  [key: string]: string | TranslationNode;
}

export type TranslationValue = string | TranslationNode;
export type TranslationDictionary = Record<UILanguage, TranslationNode>;
