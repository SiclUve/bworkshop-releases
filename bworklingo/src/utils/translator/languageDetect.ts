import { DofusLanguage } from '../../types/dofus';

/**
 * Lightweight deterministic language guesser for Dofus chat in 'auto' mode.
 * Prevents cross-language normalization collisions (e.g. ES "inv" vs PT "inv" vs EN "inv",
 * or PT "pra" vs FR "pour") before calling GTX or offline rules.
 */
export function guessChatLanguage(text: string): DofusLanguage {
  if (!text || !text.trim()) return 'fr';
  const lower = text.toLowerCase();

  const scores: Record<DofusLanguage, number> = {
    fr: 0,
    en: 0,
    es: 0,
    pt: 0
  };

  // Distinctive script & punctuation signals
  if (/[¿¡ñ]/i.test(lower)) scores.es += 4;
  if (/[ãõ]/i.test(lower)) scores.pt += 4;
  if (/[ç]/i.test(lower)) {
    if (/(?:ça|garçon|façon)/i.test(lower)) scores.fr += 3;
    if (/(?:calabouço|prospecção|redução|poço|forjalança|caça)/i.test(lower)) scores.pt += 4;
  }
  if (/[éèêàù]/i.test(lower)) scores.fr += 1.5;

  // Distinctive French chat markers
  const frPatterns = [
    /\b(?:je|tu|on|nous|vous|ils|elles|ça|sa|c'est|j'ai|jai|chui|chuis|jsuis|jss|kelkun|qqun|qqn)\b/g,
    /\b(?:svp|stp|bjr|slt|mrc|tkt|dsl|bcp|pck|pk|pr|dj|donjon|cherche|recrute|vends|ach[eè]te)\b/g,
    /\b(?:qui\s+(?:pour|veut|est|g[eè]re)|taper|avec|sans|dans|pour|chez|quoi|combien|glaces?)\b/g
  ];
  for (const p of frPatterns) {
    const m = lower.match(p);
    if (m) scores.fr += m.length * 2;
  }

  // Distinctive English chat markers
  const enPatterns = [
    /\b(?:the|and|for|with|from|without|this|that|you|are|i'm|im|we|they|who|what|where)\b/g,
    /\b(?:lf|lfg|lfm|wtb|wts|wtt|looking|spots?|carry|dungeon|pls|plz|thx|ty|np|omw|idk|anyone|melee|destroyers?)\b/g
  ];
  for (const p of enPatterns) {
    const m = lower.match(p);
    if (m) scores.en += m.length * 2;
  }

  // Distinctive Spanish chat markers
  const esPatterns = [
    /\b(?:busco|recluto|mazmorra|mazmos?|reca|recas|recaudadores?|porfa|xfa|grax|grasias|gracias|hola|wenas|bnas)\b/g,
    /\b(?:quien|qui[eé]n|kien|kn|alguien|cupos?|plazas?|llaves?|manojo|tmb|dnd|para|con|sin|estoy|toy|vamos|puedo|pasa|pasar)\b/g,
    /\b(?:jalat[oó]|yopuka|ocra|zurcar[aá]k|anutrof|aniripsa|sacr[oó]grito|tymador|selotrop|hipermago|dragocerdo|roble|maxilubo|devastadores?)\b/g
  ];
  for (const p of esPatterns) {
    const m = lower.match(p);
    if (m) scores.es += m.length * 2.2;
  }

  // Distinctive Portuguese chat markers
  const ptPatterns = [
    /\b(?:procuro|recruto|calabou[cç]o|calas?|vaga|vagas|vlw|valeu|obg|obgd|obrigad[oa]|pfv|blz|flw|tmj|tbm|aki|cmg|ctg)\b/g,
    /\b(?:voc[eê]s?|vcs?|pra|pro|pros|pras|quem|qm|topa|algm|algu[eé]m|ngm|kd|cad[eê]|bora|não|nao|com|sem|muito|mto|mt|coletor|coletores)\b/g,
    /\b(?:papatudo|ladino|kilorf|forjalan[cç]a|kwentro|glurseleste|carvalho\s+mole|mulobo|drag[aã]o-?porco|urs[oó]baros?|pinguins?)\b/g
  ];
  for (const p of ptPatterns) {
    const m = lower.match(p);
    if (m) scores.pt += m.length * 2.2;
  }

  let bestLang: DofusLanguage = 'fr';
  let bestScore = scores.fr;
  (['en', 'es', 'pt'] as DofusLanguage[]).forEach((lang) => {
    if (scores[lang] > bestScore) {
      bestScore = scores[lang];
      bestLang = lang;
    }
  });

  return bestLang;
}
