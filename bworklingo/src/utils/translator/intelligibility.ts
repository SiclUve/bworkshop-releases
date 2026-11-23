import { DofusEntry, DofusLanguage } from '../../types/dofus';
import { DOFUS_CLASSES_ALL_LANGS } from '../../data/dofusExpandedData';
import { NOTABLE_BOSS_TOKENS, NOTABLE_MONSTER_FAMILIES_TOKENS } from './constants';
import { normalizeChatForLanguage } from './normalizers';
import { IntelligibilityAssessment } from './types';

const KNOWN_GAMING_ACRONYMS = new Set([
  'dps', 'koli', 'ldv', 'cac', 'pvp', 'pvm', 'ava', 'hdv', 'pl', 'fm', 'pa', 'pm', 'po', 'cc', 'pp',
  'dc', 'rm', 'br', 'cm', 'rn', 'rb', 'mf', 'xp', 'lvl', 'nv', 'stp', 'svp', 'pfv', 'xfa', 'vlw',
  'obg', 'tbm', 'tkt', 'mrc', 'dsl', 'mdr', 'ptdr', 'omg', 'wtf', 'afk', 'brb', 'omw', 'idk', 'lfg',
  'lfm', 'lf', 'wtb', 'wts', 'wtt', 'btw', 'dm', 'pm', 'fr', 'en', 'es', 'pt', 'ok', 'gg', 'gl',
  'hf', 'ty', 'np', 'thx', 'pls', 'plz', 'dj', 'boss', 'mob', 'mobs', 'add', 'adds', 'zaap', 'kamas',
  'dofus', 'exo', 'over', 'dofus3', 'dofus2', 'unity', 'retro', 'koli', 'songes', 'almanax', 'spot',
  'spots', 'carry', 'heal', 'tank', 'stuff', 'pack', 'drop', 'farm', 'rusher', 'rush', 'rushs'
]);

const KNOWN_HEAVY_SLANG_TOKENS = new Set([
  // French ultra-slang / phonetic / cryptic SMS
  'wsh', 'wesh', 'frr', 'frero', 'frérot', 'mskn', 'meskine', 'jsp', 'ntm', 'tg', 'fdp', 'chpr',
  'pkp', 'vtf', 'blc', 'bg', 'ptn', 'nrv', 'bzr', 'flm', 'qdn', 'tfk', 'tktp',
  'daron', 'reuf', 'rebeu', 'chelou', 'cheum', 'vénère', 'venere', 'oim', 'chanmé', 'chanme',
  'pélo', 'fonsdé', 'kiff', 'kiffe', 'zehef', 'miskin', 'walou', 'tarpin', 'guez', 'merguez',
  'éclaté', 'eclate', 'claqué', 'claque', 'wallah', 'starf', 'tfou', 'vitef',
  'jvé', 'tfre', 'trc', 'dtt', 'dutt', 'chui', 'chuis', 'jsui', 'jsuis', 'cest',
  // English ultra-slang
  'bruh', 'bro', 'fam', 'lowkey', 'highkey', 'deadass', 'sus', 'nocap', 'yeet', 'sheesh',
  'smh', 'tbh', 'ngl', 'iykyk', 'fomo', 'imo', 'imho', 'rofl', 'lmao', 'lmfao', 'stfu', 'gtfo', 'fyi',
  // Spanish ultra-slang
  'oe', 'weon', 'wn', 'wbon', 'csm', 'ctm', 'ptm', 'alv', 'alvrga', 'nmms', 'nmmms', 'vrg',
  'pibe', 'boludo', 'chido', 'pana', 'broda', 'ql', 'qlo', 'kbron', 'wey', 'guey', 'manito', 'manin',
  'revento', 'reventó', 'manqueo', 'manqueando', 'trolleo', 'troleo', 'afano',
  // Portuguese ultra-slang
  'mano', 'mlk', 'muleke', 'lek', 'parça', 'parca', 'dms', 'aff', 'mds', 'krl', 'pqp', 'vsf', 'tnc',
  'kkk', 'kkkk', 'rsrs', 'sfd', 'slk', 'bugado', 'zoado', 'trolando',
  'tankando', 'tankar', 'kitando', 'kitar', 'rushando', 'nerfado', 'buffado'
]);

const STANDARD_COMMON_WORDS = new Set([
  // French
  'je', 'tu', 'il', 'elle', 'on', 'nous', 'vous', 'ils', 'elles', 'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'd', 'l',
  'et', 'ou', 'est', 'es', 'suis', 'sommes', 'etes', 'êtes', 'sont', 'a', 'as', 'ai', 'avons', 'avez', 'ont', 'va', 'vais',
  'vas', 'allons', 'allez', 'vont', 'fait', 'fais', 'faire', 'faut', 'peut', 'peux', 'veut', 'veux', 'viens', 'vient',
  'dans', 'sur', 'sous', 'avec', 'sans', 'pour', 'par', 'qui', 'que', 'quoi', 'ou', 'où', 'quand', 'comment', 'pourquoi',
  'si', 'mais', 'donc', 'car', 'ni', 'ne', 'pas', 'plus', 'tout', 'tous', 'rien', 'bien', 'mal', 'bon', 'bonne', 'trop',
  'ici', 'la', 'là', 'ca', 'ça', 'ce', 'cette', 'ces', 'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses',
  'cherche', 'recrute', 'vends', 'vend', 'achete', 'achète', 'donjon', 'groupe', 'place', 'places', 'cle', 'clé', 'cles', 'clés',
  'salut', 'bonjour', 'merci', 'svp', 'stp', 'niveau', 'combien', 'combat', 'combattre', 'aide', 'besoin', 'gere', 'gère',
  'gérer', 'chaud', 'disponible', 'monstre', 'monstres', 'famille', 'familles', 'rejoint', 'viens', 'venir', 'partir', 'mort',
  'tue', 'tuer', 'taper', 'lancer', 'lance', 'passe', 'passer', 'tour', 'tours', 'jeu', 'jouer', 'arrete', 'arrête',
  // English
  'the', 'a', 'an', 'and', 'or', 'but', 'if', 'is', 'are', 'am', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does',
  'did', 'will', 'would', 'can', 'could', 'should', 'to', 'of', 'in', 'on', 'at', 'for', 'with', 'without', 'from', 'by',
  'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'our', 'their',
  'who', 'what', 'where', 'when', 'why', 'how', 'looking', 'recruiting', 'selling', 'buying', 'dungeon', 'group', 'party',
  'spot', 'spots', 'key', 'keys', 'monster', 'monsters', 'family', 'families', 'help', 'need', 'want', 'come', 'go', 'fight',
  'play', 'please', 'thank', 'thanks', 'hello', 'hi', 'level', 'much', 'worth', 'price', 'down', 'ready',
  // Spanish
  'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del', 'al', 'y', 'o', 'pero', 'si', 'es', 'son', 'soy',
  'estoy', 'esta', 'está', 'estamos', 'estan', 'están', 'hay', 'tiene', 'tengo', 'tienes', 'hace', 'hacer', 'hago', 'vamos',
  'voy', 'va', 'van', 'puede', 'puedo', 'puedes', 'quiere', 'quiero', 'quieres', 'para', 'por', 'con', 'sin', 'en', 'sobre',
  'quien', 'quién', 'que', 'qué', 'donde', 'dónde', 'como', 'cuando', 'alguien', 'busco', 'recluto', 'vendo', 'compro',
  'mazmorra', 'mazmorras', 'grupo', 'plaza', 'plazas', 'llave', 'llaves', 'monstruo', 'monstruos', 'ayuda', 'necesito',
  'hola', 'gracias', 'nivel', 'cuanto', 'cuánto', 'cuesta', 'vale', 'pasar', 'pasa', 'combate', 'todo', 'bien', 'mal',
  // Portuguese
  'o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas', 'do', 'da', 'dos', 'das', 'de', 'no', 'na', 'nos', 'nas', 'em', 'e',
  'ou', 'mas', 'se', 'eh', 'é', 'sao', 'são', 'sou', 'estou', 'esta', 'está', 'estamos', 'tem', 'tenho', 'faz', 'fazer',
  'vamos', 'vou', 'vai', 'pode', 'posso', 'quer', 'quero', 'para', 'por', 'com', 'sem', 'quem', 'que', 'onde', 'como',
  'quando', 'alguem', 'alguém', 'procuro', 'recruto', 'vendo', 'compro', 'calabouco', 'calabouço', 'grupo', 'vaga', 'vagas',
  'chave', 'chaves', 'monstro', 'monstros', 'ajuda', 'preciso', 'ola', 'olá', 'obrigado', 'obrigada', 'nivel', 'nível',
  'quanto', 'custa', 'vale', 'passar', 'passa', 'combate', 'tudo', 'bem', 'mal', 'aqui', 'agora'
]);

function buildProtectedDofusWordSet(entries: DofusEntry[]): Set<string> {
  const words = new Set<string>();
  for (const c of DOFUS_CLASSES_ALL_LANGS) {
    [c.fr, c.en, c.es, c.pt, ...c.short].forEach((t) => {
      if (t) words.add(t.toLowerCase());
    });
  }
  for (const b of NOTABLE_BOSS_TOKENS) {
    [b.fr, b.en, b.es, b.pt, ...b.terms].forEach((t) => {
      t.toLowerCase().split(/[\s,'-]+/).forEach((w) => { if (w) words.add(w); });
    });
  }
  for (const f of NOTABLE_MONSTER_FAMILIES_TOKENS) {
    [...f.plural.terms, ...f.singular.terms, f.plural.fr, f.plural.en, f.plural.es, f.plural.pt].forEach((t) => {
      t.toLowerCase().split(/[\s,'-]+/).forEach((w) => { if (w) words.add(w); });
    });
  }
  // Light pass on dictionary entries up to avoid iterating 20k strings per single token check unnecessarily;
  // only split entries <= 40 chars
  for (let i = 0; i < Math.min(entries.length, 4000); i++) {
    const e = entries[i];
    [e.fr, e.en, e.es, e.pt].forEach((val) => {
      if (val && val.length <= 40) {
        val.toLowerCase().split(/[\s,'-]+/).forEach((w) => { if (w.length >= 3) words.add(w); });
      }
    });
  }
  return words;
}

/**
 * Evaluates whether a Dofus chat message is genuinely incomprehensible / ultra-slang /
 * heavily typoed for regex + GTX, so optional AI rescue (e.g. bworkshop quota or server Gemini)
 * is triggered ONLY when actually needed and normal messages stay 100% on free GTX.
 */
export function assessMessageIntelligibility(
  originalText: string,
  sourceLang: DofusLanguage | 'auto',
  entries: DofusEntry[] = [],
  gtxOutput?: string | null,
  targetLang?: DofusLanguage
): IntelligibilityAssessment {
  const reasons: string[] = [];
  const unknownTokens: string[] = [];

  if (!originalText || !originalText.trim()) {
    return { isIncomprehensible: false, score: 0, reasons, unknownTokens, detectedLanguage: sourceLang === 'auto' ? 'fr' : sourceLang };
  }

  // Strip chat log / command prefixes, coords, [Shift+Click] links and %macros%
  let cleaned = originalText.trim()
    .replace(/^\[\d{1,2}:\d{2}(?::\d{2})?\](?:\s*\([^)]+\))?(?:\s*(?:de|à|to|from)\s+)?(?:\s*\[?[a-zA-Z0-9À-ÿ_\-]+\]?\s*:)\s*/i, '')
    .replace(/^\/(?:w\s+(?:"[^"]+"|\'[^\']+\'|\*[^*]+\*|\S+)|r|c|t|i|p|g|k|a|b|s|m)\s+/i, '')
    .replace(/\[\s*-?\d+\s*,\s*-?\d+\s*\]/g, ' ')
    .replace(/\[[^\]]+\]/g, ' ')
    .replace(/%[a-zA-Z0-9_]+%/g, ' ');

  const { normalized, detectedLanguage } = normalizeChatForLanguage(cleaned, sourceLang);
  const protectedDofusWords = buildProtectedDofusWordSet(entries);

  // Remove standard apostrophe elisions ("j'ai", "s'il", "d'aide", "don't", "c'est") before fragment counting
  const strippedElisions = normalized
    .toLowerCase()
    .replace(/\b(?:c|d|j|l|m|n|s|t|qu)['’](?=[a-zà-ÿ])/gi, '')
    .replace(/['’](?:s|t|ll|re|ve|m|d)\b/gi, '');

  const tokens = strippedElisions
    .split(/[^a-z0-9à-ÿ]+/i)
    .filter((w) => w.length > 0 && !/^\d+$/.test(w));

  if (tokens.length === 0) {
    return { isIncomprehensible: false, score: 0, reasons, unknownTokens, detectedLanguage };
  }

  let score = 0;
  let slangHits = 0;
  let consonantClusterHits = 0;
  let elongationHits = 0;
  let singleCharFragments = 0;

  for (const tok of tokens) {
    if (KNOWN_GAMING_ACRONYMS.has(tok) || STANDARD_COMMON_WORDS.has(tok) || protectedDofusWords.has(tok)) {
      continue;
    }

    // Check explicit ultra-slang words
    if (KNOWN_HEAVY_SLANG_TOKENS.has(tok)) {
      slangHits++;
      unknownTokens.push(tok);
      continue;
    }

    // Consonant-only clusters >= 3 chars (no vowels a/e/i/o/u/y and not known acronyms)
    if (tok.length >= 3 && !/[aeiouyàáâãäèéêëìíîïòóôõöùúûü]/i.test(tok)) {
      consonantClusterHits++;
      unknownTokens.push(tok);
      continue;
    }

    // Repeated characters elongation (e.g. "mdrrrr", "nooooo", "kkkkk", "aaaa")
    if (/(.)\1{2,}/.test(tok)) {
      elongationHits++;
      unknownTokens.push(tok);
      continue;
    }

    // Broken 1-char phonetic fragments (like standalone "c", "g", "k", "n", "t")
    if (tok.length === 1 && !['a', 'à', 'y', 'o', 'e', 'i', 'u'].includes(tok)) {
      singleCharFragments++;
      unknownTokens.push(tok);
      continue;
    }

    // Digit-letter hybrid leetspeak/typos excluding kamas/levels like 2m5 / fri3 / 200kk / t1 / t2
    if (/[a-z].*\d|\d.*[a-z]/i.test(tok) && !/^(?:\d+[mk]+|f[123]|fri[123]|b[1-8]|t[1-9]\d?|[1-9]e)$/i.test(tok)) {
      score += 1.5;
      unknownTokens.push(tok);
    }
  }

  if (slangHits >= 2) {
    score += slangHits * 2;
    reasons.push(`ultra_slang(${slangHits})`);
  } else if (slangHits === 1 && tokens.length <= 5) {
    score += 2;
    reasons.push('dense_short_slang');
  }

  if (consonantClusterHits >= 1) {
    score += consonantClusterHits * 2;
    reasons.push(`unrecognized_consonant_sms(${consonantClusterHits})`);
  }

  if (elongationHits >= 1) {
    score += elongationHits * 1.5;
    reasons.push(`character_elongation(${elongationHits})`);
  }

  if (singleCharFragments >= 2) {
    score += singleCharFragments * 1.5;
    reasons.push(`broken_sms_fragments(${singleCharFragments})`);
  }

  // Post-GTX check: if GTX ran and copied 2+ cryptic unknown tokens verbatim into another language,
  // regex+GTX clearly failed to understand those tokens.
  if (gtxOutput && targetLang && detectedLanguage !== targetLang) {
    const outTokens = new Set(
      gtxOutput
        .toLowerCase()
        .split(/[^a-z0-9à-ÿ]+/i)
        .filter((w) => w.length >= 2)
    );
    const leakedTokens = unknownTokens.filter((u) => outTokens.has(u) && !KNOWN_GAMING_ACRONYMS.has(u) && !protectedDofusWords.has(u));
    if (leakedTokens.length >= 2) {
      score += leakedTokens.length * 1.5;
      reasons.push(`gtx_untranslated_tokens(${leakedTokens.join(',')})`);
    }
  }

  const isIncomprehensible = score >= 3.5;
  return {
    isIncomprehensible,
    score: Number(score.toFixed(2)),
    reasons,
    unknownTokens: Array.from(new Set(unknownTokens)),
    detectedLanguage
  };
}
