import { DofusLanguage } from '../../types/dofus';

export interface NotableBossToken {
  fr: string;
  en: string;
  es: string;
  pt: string;
  terms: string[];
}

export interface MonsterFamilyVariant {
  fr: string;
  en: string;
  es: string;
  pt: string;
  terms: string[];
}

export interface NotableMonsterFamilyToken {
  plural: MonsterFamilyVariant;
  singular: MonsterFamilyVariant;
}

export type MultiLangRuleMap =
  | Record<DofusLanguage, string>
  | ((match: string, ...args: any[]) => Record<DofusLanguage, string>);

export interface MultiLangTokenRule {
  pattern: RegExp;
  map: MultiLangRuleMap;
}

export interface IntelligibilityAssessment {
  isIncomprehensible: boolean;
  score: number;
  reasons: string[];
  unknownTokens: string[];
  detectedLanguage: DofusLanguage;
}
