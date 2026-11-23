export type DofusLanguage = 'fr' | 'en' | 'es' | 'pt';

export interface DofusEntry {
  fr: string;
  en: string;
  es?: string;
  pt?: string;
  aliases_fr: string[];
  aliases_en?: string[];
  category: string;
  context_sensitive: boolean;
  status?: string;
  note: string;
  origin?: string;
  source_url?: string;
  source_kind?: string;
  evidence?: string;
}

export interface AliasConflict {
  surface_form: string;
  candidate_translations: {
    en: string;
    entries: string[];
  }[];
}

export interface DofusDictionaryData {
  meta?: {
    project: string;
    as_of: string;
    languages: string[];
    total_entry_count: number;
    cautions: string[];
  };
  metadata?: Record<string, any>;
  entries: DofusEntry[];
  alias_conflicts?: AliasConflict[];
}

export interface DetectedTerm {
  source: string;
  fr: string;
  en: string;
  es?: string;
  pt?: string;
  targetValue?: string;
  category: string;
  note?: string;
  context_sensitive?: boolean;
}

export interface TranslationRecord {
  id: string;
  originalText: string;
  translatedText: string;
  sourceLang: DofusLanguage;
  targetLang: DofusLanguage;
  timestamp: number;
  engine: 'gemini-3.8-flash' | 'ai_smart_rescue' | 'dictionary_fallback' | 'offline_rules' | 'offline_universal' | 'neural_dofus_gtx';
  detectedTerms?: DetectedTerm[];
  isFavorite?: boolean;
}

export interface OverlayConfig {
  opacity: number;
  autoCopy: boolean;
  soundEnabled: boolean;
  autoTranslateOnPaste: boolean;
  compactMode: boolean;
  position: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'center';
}
