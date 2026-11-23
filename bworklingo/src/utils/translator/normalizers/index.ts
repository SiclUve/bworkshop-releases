import { DofusLanguage } from '../../../types/dofus';
import { guessChatLanguage } from '../languageDetect';
import { normalizeFrenchGamingChat } from './french';
import { normalizeEnglishGamingChat } from './english';
import { normalizeIberianGamingChat } from './iberian';

export { normalizeFrenchGamingChat, normalizeEnglishGamingChat, normalizeIberianGamingChat };

/**
 * Normalizes Dofus gaming chat according to sourceLang (avoiding cross-language
 * collisions in 'auto' mode by guessing the dominant language first).
 */
export function normalizeChatForLanguage(text: string, sourceLang: DofusLanguage | 'auto'): { normalized: string; detectedLanguage: DofusLanguage } {
  const effectiveLang = sourceLang === 'auto' ? guessChatLanguage(text) : sourceLang;
  if (effectiveLang === 'fr') return { normalized: normalizeFrenchGamingChat(text), detectedLanguage: 'fr' };
  if (effectiveLang === 'en') return { normalized: normalizeEnglishGamingChat(text), detectedLanguage: 'en' };
  if (effectiveLang === 'es') return { normalized: normalizeIberianGamingChat(text, 'es'), detectedLanguage: 'es' };
  return { normalized: normalizeIberianGamingChat(text, 'pt'), detectedLanguage: 'pt' };
}
