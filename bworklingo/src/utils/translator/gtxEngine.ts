import { DofusEntry, DofusLanguage } from '../../types/dofus';
import { DOFUS_CLASSES_ALL_LANGS } from '../../data/dofusExpandedData';
import { DOFUS_QUESTS_AND_BOUNTIES_ENTRIES } from '../../data/dofusQuestsAndBounties';
import {
  GENERIC_CONVERSATIONAL_WORDS,
  NOTABLE_BOSS_TOKENS,
  NOTABLE_MONSTER_FAMILIES_TOKENS,
  escapeRegExp
} from './constants';
import { normalizeChatForLanguage } from './normalizers';
import { MULTI_LANG_TOKEN_RULES } from './tokenRules';

const gtxCache = new Map<string, { text: string; effectiveTarget: DofusLanguage }>();

export function polishEnglishArticles(text: string): string {
  return text
    .replace(/\bun\s+(?=[A-Z])/g, 'a ')
    .replace(/\bune\s+(?=[A-Z])/g, 'a ')
    .replace(/\bdes\s+(?=[A-Z])/g, '')
    .replace(/\ble\s+(?=[A-Z])/g, 'the ')
    .replace(/\bla\s+(?=[A-Z])/g, 'the ')
    .replace(/\bles\s+(?=[A-Z])/g, 'the ')
    .replace(/\bdu\s+(?=[A-Z])/g, 'of the ')
    .replace(/\ba\s+(?=[aeiouAEIOU]|AP\b|MP\b)/g, 'an ')
    .replace(/\bA\s+(?=[aeiouAEIOU]|AP\b|MP\b)/g, 'An ')
    .replace(/\s{2,}/g, ' ');
}

/**
 * Executes a cached GTX query and handles auto-source === target language flipping cleanly.
 */
async function queryGtxEndpoint(
  queryText: string,
  sourceLang: DofusLanguage | 'auto',
  targetLang: DofusLanguage
): Promise<{ text: string; effectiveTarget: DofusLanguage } | null> {
  const slParam = sourceLang === 'auto' ? 'auto' : sourceLang;
  let effectiveTarget = targetLang;
  const fullUrl = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${slParam}&tl=${effectiveTarget}&dt=t&q=${encodeURIComponent(queryText)}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 4500);

  try {
    const res = await fetch(fullUrl, { signal: controller.signal });
    clearTimeout(timer);
    if (!res.ok) return null;
    const data = await res.json();
    const detectedLang = data[2] as string;

    if (sourceLang === 'auto' && detectedLang === targetLang) {
      effectiveTarget = targetLang === 'fr' ? 'en' : 'fr';
      const altUrl = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${detectedLang}&tl=${effectiveTarget}&dt=t&q=${encodeURIComponent(queryText)}`;
      const altRes = await fetch(altUrl);
      if (altRes.ok) {
        const altData = await altRes.json();
        return { text: altData[0].map((s: any) => s[0]).join('') as string, effectiveTarget };
      }
    }

    return { text: data[0].map((s: any) => s[0]).join('') as string, effectiveTarget };
  } catch {
    clearTimeout(timer);
    return null;
  }
}

/**
 * Client-side & Server-compatible Neural Dofus Translator.
 * Queries the public CORS-enabled GTX neural translation endpoint directly from the browser
 * while protecting all game proper nouns, [Shift+Click] links, and gaming abbreviations.
 * Works 100% without an API key and even on static hosting (bworkshop.app) or inside PiP windows.
 * Pass `options.useLexicon = false` for plain conversational small-talk translation without Dofus lexicon rules.
 */
export async function translateNeuralDofusClient(
  text: string,
  entries: DofusEntry[],
  sourceLang: DofusLanguage | 'auto',
  targetLang: DofusLanguage,
  options?: { useLexicon?: boolean }
): Promise<string | null> {
  if (!text || !text.trim() || sourceLang === targetLang) return text;
  const useLexicon = options?.useLexicon !== false;

  const cachedOnWindow = typeof window !== 'undefined' ? (window as any).__dofus_cached_entries : null;
  const allEntries: DofusEntry[] = entries && entries.length > 500
    ? entries
    : (cachedOnWindow && cachedOnWindow.length > 500
      ? cachedOnWindow
      : [...DOFUS_QUESTS_AND_BOUNTIES_ENTRIES, ...(entries || [])]);

  let chatCommandPrefix = '';
  let workingText = text.trim();

  // 1. Detect Dofus Chat Log prefix (e.g. "[17:20] (Recrutement) Joueur : ")
  const logMatch = workingText.match(/^(\[\d{1,2}:\d{2}(?::\d{2})?\](?:\s*\([^)]+\))?(?:\s*(?:de|à|to|from)\s+)?(?:\s*\[?[a-zA-Z0-9À-ÿ_\-]+\]?\s*:)[\s]*)/i);
  if (logMatch) {
    chatCommandPrefix = logMatch[1];
    workingText = workingText.slice(chatCommandPrefix.length).trim();
  } else {
    // 2. Detect Dofus Chat Command prefix (e.g. "/r ", "/w Joueur ")
    const cmdMatch = workingText.match(/^(\/(?:w\s+(?:"[^"]+"|\'[^\']+\'|\*[^*]+\*|\S+)|r|c|t|i|p|g|k|a|b|s|m)\s+)/i);
    if (cmdMatch) {
      chatCommandPrefix = cmdMatch[1];
      workingText = workingText.slice(chatCommandPrefix.length).trim();
    }
  }

  const trimmed = workingText;
  if (!trimmed) return text;

  // Small-talk / free-chat bypass when Dofus lexicon mode is explicitly disabled
  if (!useLexicon) {
    const cacheKey = `nolx|${sourceLang}|${targetLang}|${trimmed}`;
    let cached = gtxCache.get(cacheKey);
    if (!cached) {
      const fetched = await queryGtxEndpoint(trimmed, sourceLang, targetLang);
      if (!fetched) return null;
      if (gtxCache.size >= 300) gtxCache.delete(gtxCache.keys().next().value as string);
      gtxCache.set(cacheKey, fetched);
      cached = fetched;
    }
    return chatCommandPrefix ? `${chatCommandPrefix}${cached.text}` : cached.text;
  }

  const lowerTrimmed = trimmed.toLowerCase();

  // Fast exact match check if the entire input is a single Dofus entity or [Bracketed Entity]
  const isBracketedOnly = /^\[[^\]]+\]$/.test(trimmed);
  const bareTrimmed = isBracketedOnly ? lowerTrimmed.slice(1, -1).trim() : lowerTrimmed;

  for (const item of allEntries) {
    const targetVal = item[targetLang] || item.en || item.fr;
    if (!targetVal) continue;
    const isMatch = sourceLang === 'fr'
      ? (item.fr.toLowerCase() === bareTrimmed || item.aliases_fr?.some((a: string) => a.toLowerCase() === bareTrimmed))
      : (sourceLang === 'auto'
        ? (item.fr.toLowerCase() === bareTrimmed || item.en?.toLowerCase() === bareTrimmed || item.es?.toLowerCase() === bareTrimmed || item.pt?.toLowerCase() === bareTrimmed || item.aliases_fr?.some((a: string) => a.toLowerCase() === bareTrimmed))
        : (item[sourceLang]?.toLowerCase() === bareTrimmed));
    if (isMatch) {
      const formatted = isBracketedOnly ? `[${targetVal}]` : targetVal;
      return chatCommandPrefix ? chatCommandPrefix + formatted : formatted;
    }
  }

  const tokens: { placeholder: string; target: string }[] = [];

  // Protect Dofus coordinates like [25,-18]
  let preProtected = trimmed.replace(/\[\s*-?\d+\s*,\s*-?\d+\s*\]/g, (coords) => {
    const ph = `ZzDofus${tokens.length}zZ`;
    tokens.push({ placeholder: ph, target: coords.replace(/\s+/g, '') });
    return ph;
  });

  // Protect %pos%, %xp%, %hp% macros
  preProtected = preProtected.replace(/%[a-zA-Z0-9_]+%/g, (macro) => {
    const ph = `ZzDofus${tokens.length}zZ`;
    tokens.push({ placeholder: ph, target: macro });
    return ph;
  });

  // Protect in-game [Shift+Click] bracketed links
  const bracketProtected = preProtected.replace(/\[([^\]]+)\]/g, (fullMatch, innerText) => {
    const cleanInner = innerText.trim();
    if (/^(?:pl|b8|b4|xp|pvm|pvp|ava|fm)$/i.test(cleanInner)) {
      const ph = `ZzDofus${tokens.length}zZ`;
      tokens.push({ placeholder: ph, target: `[${cleanInner.toUpperCase()}]` });
      return ph;
    }

    let qtyPrefix = '';
    let qtySuffix = '';
    let nameToLookup = cleanInner;

    const prefixMatch = cleanInner.match(/^(\d+\s*x?\s*|\s*x\s*\d+\s*)/i);
    if (prefixMatch && prefixMatch[1].length < cleanInner.length) {
      qtyPrefix = prefixMatch[1];
      nameToLookup = cleanInner.slice(qtyPrefix.length).trim();
    } else {
      const suffixMatch = cleanInner.match(/(\s*x\s*\d+|\s+\d+)$/i);
      if (suffixMatch && suffixMatch[1].length < cleanInner.length) {
        qtySuffix = suffixMatch[1];
        nameToLookup = cleanInner.slice(0, -qtySuffix.length).trim();
      }
    }
    const lowerLookup = nameToLookup.toLowerCase();

    for (const item of allEntries) {
      const targetVal = item[targetLang] || item.en || item.fr;
      if (!targetVal) continue;
      const isMatch = sourceLang === 'fr'
        ? (item.fr.toLowerCase() === lowerLookup || item.aliases_fr?.some((a: string) => a.toLowerCase() === lowerLookup))
        : (sourceLang === 'auto'
          ? (item.fr.toLowerCase() === lowerLookup || item.en?.toLowerCase() === lowerLookup || item.es?.toLowerCase() === lowerLookup || item.pt?.toLowerCase() === lowerLookup || item.aliases_fr?.some((a: string) => a.toLowerCase() === lowerLookup))
          : (item[sourceLang]?.toLowerCase() === lowerLookup));
      if (isMatch) {
        const ph = `ZzDofus${tokens.length}zZ`;
        tokens.push({ placeholder: ph, target: `[${qtyPrefix}${targetVal}${qtySuffix}]` });
        return ph;
      }
    }
    return fullMatch;
  });

  // Intra-language cleaning (uses guessChatLanguage in 'auto' mode to avoid cross-language collisions)
  let { normalized: cleaned } = normalizeChatForLanguage(bracketProtected, sourceLang);

  const addToken = (
    pattern: RegExp,
    target: string | Record<DofusLanguage, string> | ((match: string, ...args: any[]) => Record<DofusLanguage, string> | string)
  ) => {
    pattern.lastIndex = 0;
    cleaned = cleaned.replace(pattern, (match, ...args) => {
      let resolvedTarget: any = typeof target === 'function' ? target(match, ...args) : target;
      if (typeof resolvedTarget === 'object' && resolvedTarget !== null) {
        resolvedTarget = resolvedTarget[targetLang] || resolvedTarget.en || resolvedTarget.fr;
      }
      if (typeof resolvedTarget === 'string') {
        for (let i = 0; i < args.length; i++) {
          if (typeof args[i] === 'string' || typeof args[i] === 'number') {
            resolvedTarget = resolvedTarget.replace(new RegExp(`\\$${i + 1}`, 'g'), String(args[i]));
          }
        }
      }
      const ph = `ZzDofus${tokens.length}zZ`;
      tokens.push({ placeholder: ph, target: String(resolvedTarget) });
      return ph;
    });
    pattern.lastIndex = 0;
  };

  // 1. Compound Dungeons across all languages
  const allDungeonBosses = [...NOTABLE_BOSS_TOKENS];
  for (const entry of allEntries) {
    if (entry.category === 'boss' || entry.category === 'monster' || (entry.fr && (entry.fr.includes('Comte') || entry.fr.includes('Nidas')))) {
      allDungeonBosses.push({
        fr: entry.fr,
        en: entry.en || entry.fr,
        es: entry.es || entry.en || entry.fr,
        pt: entry.pt || entry.en || entry.fr,
        terms: [entry.fr, entry.en, entry.es, entry.pt, ...(entry.aliases_fr || [])].filter(Boolean) as string[]
      });
    }
  }

  for (const b of allDungeonBosses) {
    for (const term of (b.terms || [])) {
      if (!term || term.length < 2) continue;
      const termRegex = escapeRegExp(term);

      // FR: dj <boss>, donjon <boss>
      const frDjRegex = new RegExp(`(?:^|\\b)(?:dj|donjon)(?:\\s+(?:du|de\\s+la|des|de\\s+l['']|d['']|de))?\\s+${termRegex}(?=\\s|$|[-.,?!/])`, 'gi');
      if (frDjRegex.test(cleaned)) {
        const tgt = targetLang === 'en' ? `${b.en} Dungeon` : (targetLang === 'es' ? `Mazmorra ${b.es}` : (targetLang === 'pt' ? `Calabouço ${b.pt}` : `donjon ${b.fr}`));
        addToken(frDjRegex, tgt);
      }

      // EN: <boss> dungeon
      const enDjRegex = new RegExp(`(?:^|\\b)${termRegex}\\s+dungeon(?=\\s|$|[-.,?!/])`, 'gi');
      if (enDjRegex.test(cleaned)) {
        const tgt = targetLang === 'fr' ? `donjon ${b.fr}` : (targetLang === 'es' ? `Mazmorra ${b.es}` : (targetLang === 'pt' ? `Calabouço ${b.pt}` : `${b.en} Dungeon`));
        addToken(enDjRegex, tgt);
      }

      // ES: mazmorra <boss>, mazmo <boss>
      const esDjRegex = new RegExp(`(?:^|\\b)(?:mazmorra|mazmo)(?:\\s+(?:de\\s+la|del|de))?\\s+${termRegex}(?=\\s|$|[-.,?!/])`, 'gi');
      if (esDjRegex.test(cleaned)) {
        const tgt = targetLang === 'fr' ? `donjon ${b.fr}` : (targetLang === 'en' ? `${b.en} Dungeon` : (targetLang === 'pt' ? `Calabouço ${b.pt}` : `Mazmorra ${b.es}`));
        addToken(esDjRegex, tgt);
      }

      // PT: calabouço <boss>, cala <boss>
      const ptDjRegex = new RegExp(`(?:^|\\b)(?:calabou[çc]o|cala)(?:\\s+(?:do|da|de))?\\s+${termRegex}(?=\\s|$|[-.,?!/])`, 'gi');
      if (ptDjRegex.test(cleaned)) {
        const tgt = targetLang === 'fr' ? `donjon ${b.fr}` : (targetLang === 'en' ? `${b.en} Dungeon` : (targetLang === 'es' ? `Mazmorra ${b.es}` : `Calabouço ${b.pt}`));
        addToken(ptDjRegex, tgt);
      }
    }
  }

  // 2. Token rules
  for (const rule of MULTI_LANG_TOKEN_RULES) {
    rule.pattern.lastIndex = 0;
    if (rule.pattern.test(cleaned)) {
      rule.pattern.lastIndex = 0;
      addToken(rule.pattern, rule.map);
      rule.pattern.lastIndex = 0;
    }
  }

  // 3. Classes in all languages
  for (const c of DOFUS_CLASSES_ALL_LANGS) {
    const terms = [c.fr, c.en, c.es, c.pt, ...c.short];
    for (const term of terms) {
      if (!term || term.length < 3) continue;
      const clsRegex = new RegExp(`(?:^|\\b)${escapeRegExp(term)}(?=\\s|$|[-.,?!/])`, 'gi');
      if (clsRegex.test(cleaned)) {
        addToken(clsRegex, c[targetLang]);
      }
    }
  }

  // 4. Bosses short names (when standing alone without dungeon keyword)
  for (const b of NOTABLE_BOSS_TOKENS) {
    for (const term of b.terms) {
      if (!term || term.length < 3) continue;
      const bRegex = new RegExp(`(?:^|\\b)${escapeRegExp(term)}(?=\\s|$|[-.,?!/])`, 'gi');
      if (bRegex.test(cleaned)) {
        addToken(bRegex, b[targetLang]);
      }
    }
  }

  // 4b. Monster families & notable mobs
  for (const fam of NOTABLE_MONSTER_FAMILIES_TOKENS) {
    for (const term of fam.plural.terms) {
      if (!term || term.length < 3) continue;
      const famRegex = new RegExp(`(?:^|\\b)${escapeRegExp(term)}(?=\\s|$|[-.,?!/])`, 'gi');
      if (famRegex.test(cleaned)) {
        addToken(famRegex, fam.plural[targetLang]);
      }
    }
    for (const term of fam.singular.terms) {
      if (!term || term.length < 3) continue;
      const famRegex = new RegExp(`(?:^|\\b)${escapeRegExp(term)}(?=\\s|$|[-.,?!/])`, 'gi');
      if (famRegex.test(cleaned)) {
        addToken(famRegex, fam.singular[targetLang]);
      }
    }
  }

  // 5. Proper nouns from Encyclopedia
  const lowerCleaned = cleaned.toLowerCase();
  const matchedPairs: { cand: string; target: string }[] = [];

  for (const entry of allEntries) {
    const targetVal = entry[targetLang];
    if (!targetVal) continue;

    let candidates: string[] = [];
    if (sourceLang === 'fr') {
      candidates = [entry.fr, ...(entry.aliases_fr || [])];
    } else if (sourceLang === 'en') {
      candidates = entry.en ? [entry.en] : [];
    } else if (sourceLang === 'es') {
      candidates = entry.es ? [entry.es] : [];
    } else if (sourceLang === 'pt') {
      candidates = entry.pt ? [entry.pt] : [];
    } else {
      candidates = [entry.fr, ...(entry.aliases_fr || []), entry.en, entry.es, entry.pt].filter(Boolean) as string[];
    }

    for (const cand of candidates) {
      if (!cand || cand.length < 3) continue;
      const candLower = cand.toLowerCase().trim();
      if (GENERIC_CONVERSATIONAL_WORDS.has(candLower)) continue;
      if (/^(?:niveau|level|nivel|n[ií]vel)\s+\d+$/i.test(candLower)) continue;
      if (entry.context_sensitive && !candLower.includes(' ')) continue;

      if (lowerCleaned.includes(candLower)) {
        matchedPairs.push({ cand, target: targetVal });
      }
    }
  }

  matchedPairs.sort((a, b) => b.cand.length - a.cand.length);
  for (const pair of matchedPairs) {
    addToken(new RegExp(`(?:^|\\b)${escapeRegExp(pair.cand)}(?=\\s|$|[-.,?!/])`, 'gi'), pair.target);
  }

  // 6. Call GTX translation endpoint
  let effectiveTarget = targetLang;
  try {
    const cacheKey = sourceLang + '|' + targetLang + '|' + cleaned;
    let cached = gtxCache.get(cacheKey);
    if (!cached) {
      const fetched = await queryGtxEndpoint(cleaned, sourceLang, targetLang);
      if (!fetched) return null;
      if (gtxCache.size >= 300) gtxCache.delete(gtxCache.keys().next().value as string);
      gtxCache.set(cacheKey, fetched);
      cached = fetched;
    }
    let result = cached.text;
    effectiveTarget = cached.effectiveTarget;

    // 7. Restore tokens in reverse order with multi-round resolution for nested tokens
    for (let round = 0; round < 3; round++) {
      let anyReplaced = false;
      for (let i = tokens.length - 1; i >= 0; i--) {
        const phRegex = new RegExp(`(?:Zz|ZZ|zz)[\\s_\\-]*Dofus[\\s_\\-]*${i}[\\s_\\-]*(?:zZ|ZZ|zz)`, 'gi');
        if (phRegex.test(result)) {
          result = result.replace(phRegex, tokens[i].target);
          anyReplaced = true;
        }
      }
      if (!anyReplaced) break;
    }

    // 8. Post-processing polish
    if (effectiveTarget === 'en') {
      result = polishEnglishArticles(result);
      result = result.replace(/^Recruits\b/i, 'Recruiting');
      result = result.replace(/\b1\s+spots\b/gi, '1 spot');
      result = result.replace(/\bthe\s+DJ\b/g, 'the dungeon');
      result = result.replace(/\bDJ\b/g, 'dungeon');
      result = result.replace(/\bice\s*creams?\b/gi, 'ice');
      result = result.replace(/\b(?:state\s+of\s+gravity|gravity\s+state)\b/gi, 'Heavy state');
      result = result.replace(/\b(my|your|his|her|their|our)\s+person\b/gi, '$1 character');
      // Protect Dofus Ravageurs from being translated as 'pests'
      result = result.replace(/\bthe\s+pests?\b/gi, 'the Destroyers');
      result = result.replace(/\bpest\s+mobs?\b/gi, 'Destroyer mobs');
      result = result.replace(/\bpests\s+mobs?\b/gi, 'Destroyer mobs');
      result = result.replace(/\bpests\b/gi, 'Destroyers');
      result = result.replace(/\bpest\b/gi, 'Destroyer');

      // Prevent "poop" mistranslation for CAC
      result = result.replace(/\b(?:watch\s+out\s+for\s+the\s+poop|the\s+poop)\b/gi, 'watch out for melee');
      result = result.replace(/\bpoop\b/gi, 'melee');

      // Prevent "hitting a neck" mistranslation for Gourlo
      result = result.replace(/\b(?:hitting\s+a\s+neck|hit\s+a\s+neck)\b/gi, 'fighting Gourlo the Terrible');

      // Natural gaming phrasing
      result = result.replace(/,\s*what\s+do\s+you\s+think\s*\?/gi, ', are you down?');
      result = result.replace(/\btells\s+you\s*\?/gi, 'are you down?');
      result = result.replace(/\bwho\s+wants\s+to\s+make\s+a\s+/gi, 'who wants to do a ');
      result = result.replace(/\bwho\s+wants\s+to\s+make\s+/gi, 'who wants to do ');
    } else if (effectiveTarget === 'fr') {
      result = result.replace(/\bDJ\b/g, 'donjon');
      result = result.replace(/\bLF\b/gi, 'cherche');
      result = result.replace(/\bspots?\b/gi, 'places');
      result = result.replace(/\b1\s+places\b/gi, '1 place');
      result = result.replace(/\blooking\s+for\b/gi, 'cherche');
      result = result.replace(/\b(?:la\s+)?r[eé]alisation\s+(succ[eéèê]s\s+[a-zA-ZÀ-ÿ0-9'\-]+)\b/gi, '$1');
      result = result.replace(/\br[eé]ussir\s+(zombie|hardi|collant|pusillanime|statue|nomade|duo)\b/gi, 'succès $1');
      result = result.replace(/\bporter\s+(?:un\s+|le\s+|les\s+)?(donjon|boss|fri[123]|korriandre|nidas|comte)\b/gi, 'gérer $1');
      result = result.replace(/\b(?:l')?[eé]vier\s*(?:AP|PA|MP|PM)?\b/gi, 'puits PA');
      result = result.replace(/\blavabo\b/gi, 'puits');
      result = result.replace(/\bplaquage\b/gi, 'tacle');
      result = result.replace(/\b(?:le\s+)?patron\b/gi, 'boss');
      result = result.replace(/\b(?:la\s+)?foule\b/gi, 'monstres');
      result = result.replace(/\bsangsues?\b/gi, 'PL');
      result = result.replace(/\bligne\s+de\s+mire\b/gi, 'ligne de vue');
    } else if (effectiveTarget === 'es') {
      result = result.replace(/\bDJ\b/g, 'mazmorra');
      result = result.replace(/\bhelados?\b/gi, 'hielo');
      result = result.replace(/\b(\d+)\s+lugares\s+(disponibles?|libres?|para)\b/gi, '$1 plazas $2');
      result = result.replace(/\bquedan\s+(\d+)\s+lugares\b/gi, 'quedan $1 plazas');
      result = result.replace(/\bplagas?\b/gi, 'Devastadores');
    } else if (effectiveTarget === 'pt') {
      result = result.replace(/\bDJ\b/g, 'calabouço');
      result = result.replace(/\bsorvetes?\b/gi, 'gelo');
      result = result.replace(/\b(\d+)\s+lugares\s+(dispon[ií]veis?|para)\b/gi, '$1 vagas $2');
      result = result.replace(/\brestam\s+(\d+)\s+lugares\b/gi, 'restam $1 vagas');
      result = result.replace(/\bpragas?\b/gi, 'Devastadores');
    }

    const trimmedResult = result.trim();
    return chatCommandPrefix ? chatCommandPrefix + trimmedResult : trimmedResult;
  } catch {
    return null;
  }
}
