import { DofusDictionaryData, DofusEntry, DetectedTerm, DofusLanguage } from '../types/dofus';
import { 
  DOFUS_DIMENSIONS_AND_ZONES, 
  DOFUS_CLASSES_FR_EN, 
  DOFUS_ARCHIMONSTERS_AND_WANTED 
} from './dofusExpandedData';
import { getAllExpandedDofusEntries } from './dofusQuestsAndBounties';

let cachedData: DofusDictionaryData | null = null;
let isLoading = false;
let loadPromise: Promise<DofusDictionaryData | null> | null = null;

export interface CategoryMeta {
  label: string;
  labels: Record<DofusLanguage, string>;
  icon: string;
  description: string;
}

export const CATEGORY_LABELS: Record<string, CategoryMeta> = {
  quests: {
    label: 'Quêtes & Dofus',
    labels: { fr: 'Quêtes & Dofus', en: 'Quests & Dofus', es: 'Misiones & Dofus', pt: 'Missões & Dofus' },
    icon: '📜',
    description: 'Éternelle Moisson, Six sur Six, Dofus Ocre/Vulbis/Ivoire, Alignement, Dalles...'
  },
  bounties_and_hunting: {
    label: 'Avis & Chasses',
    labels: { fr: 'Avis & Chasses', en: 'Wanted & Hunts', es: 'Se busca & Tesoros', pt: 'Procurados & Caças' },
    icon: '🎯',
    description: 'Avis de recherche (Bounty), Archimonstres, Pierre d\'âme, Chasse au trésor, Portails...'
  },
  combat: {
    label: 'Combat & Mécaniques',
    labels: { fr: 'Combat & Mécaniques', en: 'Combat & Mechanics', es: 'Combate & Mecánicas', pt: 'Combate & Mecânicas' },
    icon: '⚔️',
    description: 'PA, PM, PO, CAC, Ligne de vue, Retrait, Esquive, Tacle, Fuite...'
  },
  combat_and_states: {
    label: 'États & Rôles',
    labels: { fr: 'États & Rôles', en: 'States & Roles', es: 'Estados & Roles', pt: 'Estados & Papéis' },
    icon: '🛡️',
    description: 'Pesanteur, Invulnérable, Insoignable, Burst, DPS, Tank, Placeur...'
  },
  characteristics: {
    label: 'Caractéristiques',
    labels: { fr: 'Caractéristiques', en: 'Characteristics', es: 'Características', pt: 'Características' },
    icon: '📊',
    description: 'Vitalité, Force, Intel, Agi, Puissance, Do Pou, Résistances...'
  },
  equipment: {
    label: 'Équipements',
    labels: { fr: 'Équipements', en: 'Equipment', es: 'Equipamiento', pt: 'Equipamentos' },
    icon: '👑',
    description: 'Panoplie, Coiffe, Cape, Anneau, Dofus, Trophée, Montilier...'
  },
  smithmagic: {
    label: 'Forgemagie (FM)',
    labels: { fr: 'Forgemagie (FM)', en: 'Maging (FM)', es: 'Forjamagia (FM)', pt: 'Forjamagia (FM)' },
    icon: '🔨',
    description: 'Exo PA/PM, Puits, Reliquat, Over, Jet perf, Trans, SC, EC...'
  },
  dungeons_and_social: {
    label: 'Donjons & Social',
    labels: { fr: 'Donjons & Social', en: 'Dungeons & Social', es: 'Mazmorras & Social', pt: 'Calabouços & Social' },
    icon: '🏰',
    description: 'Recrute, Last, 2/4, Save boss, Songes, PL Korri, Succès, Koli...'
  },
  builds_and_classes: {
    label: 'Classes & Builds',
    labels: { fr: 'Classes & Builds', en: 'Classes & Builds', es: 'Clases & Builds', pt: 'Classes & Builds' },
    icon: '🧙‍♂️',
    description: 'Hupper, Steam, Roub, Sacri, Panda tank, Mono/Multi élem, Full rox...'
  },
  trade_and_craft: {
    label: 'Commerce & Métiers',
    labels: { fr: 'Commerce & Métiers', en: 'Trade & Professions', es: 'Comercio & Oficios', pt: 'Comércio & Profissões' },
    icon: '💰',
    description: 'HDV, Vends, Achète, Prix ferme, K/u, KK, Mk, Achat revente, Craft...'
  },
  chat: {
    label: 'Chat & Communication',
    labels: { fr: 'Chat & Communication', en: 'Chat & Communication', es: 'Chat & Comunicación', pt: 'Chat & Comunicação' },
    icon: '💬',
    description: 'MP moi, Bien joué (GG), Pas de souci, Salut, Re, Attends, Osef...'
  },
  zone: {
    label: 'Zones & Dimensions',
    labels: { fr: 'Zones & Dimensions', en: 'Zones & Dimensions', es: 'Zonas & Dimensiones', pt: 'Zonas & Dimensões' },
    icon: '🗺️',
    description: 'Enutrosor (Enurado), Srambad, Xélorium, Ecaflipus, Frigost...'
  },
  zones_and_locations: {
    label: 'Zones & Sous-zones',
    labels: { fr: 'Zones & Sous-zones', en: 'Zones & Subzones', es: 'Zonas & Subzonas', pt: 'Zonas & Subzonas' },
    icon: '🗺️',
    description: 'Enutrosor (Enurado), Landes de Sidimote, Berceau d\'Alma, Frigost...'
  },
  combat_mechanics: {
    label: 'Succès & États',
    labels: { fr: 'Succès & États', en: 'Challenges & States', es: 'Retos & Estados', pt: 'Desafios & Estados' },
    icon: '⚔️',
    description: 'Mains propres (Clean Hands), Hardi (Bold), Pesanteur, Insoignable...'
  },
  spells_and_classes: {
    label: 'Sorts & Classes',
    labels: { fr: 'Sorts & Classes', en: 'Spells & Classes', es: 'Hechizos & Clases', pt: 'Feitiços & Classes' },
    icon: '✨',
    description: 'Colère de Iop, Corruption (Bribery), Puissance Sylvestre, Laisse Spirituelle...'
  },
  breeding_and_mounts: {
    label: 'Montures & Élevage',
    labels: { fr: 'Montures & Élevage', en: 'Mounts & Breeding', es: 'Monturas & Crianza', pt: 'Montarias & Criação' },
    icon: '🦃',
    description: 'Dragodindes (Dragoturkey), Muldos (Seemyool), Volkornes...'
  },
  monster: {
    label: 'Archi & Bestiaire',
    labels: { fr: 'Archi & Bestiaire', en: 'Archi & Bestiary', es: 'Archi & Bestiario', pt: 'Arqui & Bestiário' },
    icon: '👾',
    description: 'Maxi Malle, Aigripoil, Brumen, Korriandre, Nidas...'
  }
};

export function getCategoryLabel(category: string, lang: DofusLanguage = 'fr'): string {
  const meta = CATEGORY_LABELS[category];
  if (!meta) return category;
  return meta.labels[lang] || meta.labels.fr || meta.label;
}

function mergeWithExpandedEntries(baseData: DofusDictionaryData, officialEntries: DofusEntry[] = []): DofusDictionaryData {
  const expanded = [...getAllExpandedDofusEntries(), ...officialEntries];
  const existingMap = new Map<string, DofusEntry>();
  const mergedEntries = [...(baseData.entries || [])];
  for (const e of mergedEntries) {
    if (e?.fr) existingMap.set(e.fr.toLowerCase(), e);
  }

  for (const item of expanded) {
    if (!item?.fr) continue;
    const key = item.fr.toLowerCase();
    const existing = existingMap.get(key);
    if (!existing) {
      existingMap.set(key, item);
      mergedEntries.push(item);
    } else if (key !== 'roub') {
      if (item.es && !existing.es) existing.es = item.es;
      if (item.pt && !existing.pt) existing.pt = item.pt;
      if (item.aliases_fr?.length) {
        existing.aliases_fr = Array.from(new Set([...(existing.aliases_fr || []), ...item.aliases_fr]));
      }
      if (item.aliases_en?.length) {
        existing.aliases_en = Array.from(new Set([...(existing.aliases_en || []), ...item.aliases_en]));
      }
    }
  }

  return {
    ...baseData,
    entries: mergedEntries
  };
}

/**
 * Loads the community dictionary + the 2,743 official encyclopedia entries (all 1,984 quests, 31 Dofus, 96 Bounties, 306 Archmonsters, 187 Dungeons)
 */
export async function loadDofusDictionary(): Promise<DofusDictionaryData | null> {
  if (cachedData) return cachedData;
  if (loadPromise) return loadPromise;

  loadPromise = (async () => {
    isLoading = true;
    try {
      // Load both the 438 community glossary and the 18,513+ official encyclopedia entries in parallel
      // Support both relative subpath hosting (e.g., https://bworkshop.app/apps/translator/) and root hosting
      const fetchAsset = async (relPath: string) => {
        const res = await fetch(`./${relPath}`).catch(() => null);
        if (res && res.ok) return res;
        return fetch(`/${relPath}`).catch(() => null);
      };

      const [commRes, encRes] = await Promise.all([
        fetchAsset('assets/community-dictionary.json'),
        fetchAsset('assets/dofus_official_encyclopedia.json')
      ]);

      const officialEntries: DofusEntry[] = encRes && encRes.ok ? ((await encRes.json())?.entries || []) : [];

      if (commRes && commRes.ok) {
        const json = await commRes.json();
        cachedData = mergeWithExpandedEntries(json, officialEntries);
        if (typeof window !== 'undefined') (window as any).__dofus_cached_entries = cachedData.entries;
        return cachedData;
      }

      // Or server api endpoint
      const apiRes = await fetch('/api/dictionary');
      if (apiRes.ok) {
        const json = await apiRes.json();
        cachedData = mergeWithExpandedEntries(json, officialEntries);
        if (typeof window !== 'undefined') (window as any).__dofus_cached_entries = cachedData.entries;
        return cachedData;
      }
    } catch (e) {
      console.warn('Could not load dictionary file, falling back to expanded dictionary', e);
      cachedData = {
        metadata: {
          title: 'Dictionnaire Dofus Complet',
          version: '2.0',
          description: 'Lexique communautaire, quêtes et avis de recherche',
          total_entries: getAllExpandedDofusEntries().length,
          categories: {}
        },
        entries: getAllExpandedDofusEntries()
      };
      return cachedData;
    } finally {
      isLoading = false;
    }
    return null;
  })();

  return loadPromise;
}

export function getCachedDictionary(): DofusDictionaryData | null {
  return cachedData;
}

/**
 * Fast client-side rule-based translation replacement across FR / EN / ES / PT
 */
export function translateWithRules(
  text: string,
  entries: DofusEntry[],
  sourceLang: DofusLanguage,
  targetLang: DofusLanguage = 'en'
): string {
  if (!text || !entries || entries.length === 0 || sourceLang === targetLang) return text;

  let result = text;
  const lowerInput = text.toLowerCase();
  const sorted = [...entries].sort((a, b) => {
    const lenA = (a[sourceLang] || a.fr || '').length;
    const lenB = (b[sourceLang] || b.fr || '').length;
    return lenB - lenA;
  });

  for (const entry of sorted) {
    const targetVal = entry[targetLang] || entry.en || entry.fr;
    if (!targetVal) continue;
    const candidates = sourceLang === 'fr'
      ? [entry.fr, ...(entry.aliases_fr || [])]
      : [entry[sourceLang] || ''];

    for (const cand of candidates) {
      if (!cand || cand.length < 2) continue;
      if (!lowerInput.includes(cand.toLowerCase())) continue;
      const regex = new RegExp(`(?:^|\\b)${escapeRegExp(cand)}(?=\\s|$|[.,?!])`, 'gi');
      result = result.replace(regex, (match) => matchCase(match, targetVal));
    }
  }

  return result;
}

/**
 * Detect Dofus specific terms within input text across FR / EN / ES / PT
 */
export function detectDofusTerms(
  text: string,
  entries: DofusEntry[],
  sourceLang: DofusLanguage,
  targetLang: DofusLanguage = 'en'
): DetectedTerm[] {
  if (!text) return [];

  const found: DetectedTerm[] = [];
  const lower = text.toLowerCase();
  const seen = new Set<string>();
  const seenSource = new Set<string>();

  const grammarStopWords = new Set([
    'de', 'dé', 'du', 'des', 'le', 'la', 'les', 'un', 'une', 'ou', 'où', 'et', 'est', 'es', 'en', 'au', 'aux',
    'on', 'tu', 'je', 'il', 'ils', 'elle', 'elles', 'nous', 'vous', 'ce', 'cet', 'cette', 'ces', 'se', 'sa', 'son', 'ses',
    'ma', 'mon', 'mes', 'ta', 'ton', 'tes', 'ne', 'ni', 'si', 'va', 'vas', 'vais', 'as', 'ai', 'a', 'à', 'an', 'ans',
    'os', 'or', 'par', 'sur', 'sous', 'dans', 'avec', 'sans', 'pour', 'vers', 'chez', 'mais', 'donc', 'car', 'qui', 'que',
    'quoi', 'dont', 'pas', 'plus', 'tout', 'tous', 'toute', 'toutes', 'rien', 'bien', 'mal', 'peu', 'très', 'tres',
    'bon', 'bonne', 'beau', 'belle', 'grand', 'petit', 'même', 'meme', 'autre', 'autres', 'ici', 'là',
    'oui', 'non', 'moi', 'toi', 'lui', 'eux', 'leur', 'leurs', 'notre', 'votre', 'nos', 'vos', 'été', 'ete', 'fait',
    'fais', 'faire', 'dit', 'dire', 'mis', 'pris', 'vu', 'su', 'pu', 'dû', 'eu', 'avoir', 'être', 'etre',
    'accord', 'trace', 'saluer', 'rire', 'danser', 'joie', 'coucou', 'rêve', 'animal',
    'em', 'no', 'na', 'nos', 'nas', 'do', 'da', 'dos', 'das', 'ao', 'aos', 'com', 'sem', 'por', 'para', 'con', 'sin', 'el', 'al'
  ]);

  // Detect PT / ES specific Dofus terms first (e.g. coletores / recaudadores -> percepteurs)
  if ((sourceLang === 'pt' || sourceLang === 'es') && /\b(?:coletores?|recaudadores?|recas?)\b/i.test(lower)) {
    const m = lower.match(/\b(coletores?|recaudadores?|recas?)\b/i);
    if (m) {
      const targetPerco = targetLang === 'fr' ? 'percepteurs' : targetLang === 'en' ? 'perceptors' : targetLang === 'es' ? 'recaudadores' : 'coletores';
      seen.add('percepteur');
      seenSource.add(m[1].toLowerCase());
      found.push({
        source: m[1],
        fr: 'Percepteur',
        en: 'Perceptor',
        es: 'Recaudador',
        pt: 'Coletor',
        targetValue: targetPerco,
        category: 'dungeons_and_social',
        note: 'Entité de guilde posée pour récolter des ressources et de l\'XP'
      });
    }
  }

  const allEntries = entries && entries.length > 500
    ? entries
    : [...getAllExpandedDofusEntries(), ...(entries || [])];

  // Check all dictionary entries (Quests, Bounties, Archmonsters, Spells, Achievements, Community)
  for (const entry of allEntries) {
    const candidates = sourceLang === 'fr'
      ? [entry.fr, ...(entry.aliases_fr || [])]
      : [entry[sourceLang] || ''];

    for (const cand of candidates) {
      if (!cand || cand.length < 2) continue;
      const candLower = cand.toLowerCase().trim();
      if (grammarStopWords.has(candLower)) continue;
      if (/^(?:niveau|level|nivel|nível)\s+\d+$/i.test(candLower)) continue;
      if (!lower.includes(candLower)) continue;
      const frKey = entry.fr.toLowerCase();
      if (seen.has(frKey) || seenSource.has(candLower)) break;

      const regex = new RegExp(`(?:^|\\b)${escapeRegExp(cand)}(?=\\s|$|[.,?!\\]\\-/])`, 'i');
      if (regex.test(lower)) {
        seen.add(frKey);
        seenSource.add(candLower);
        found.push({
          source: cand,
          fr: entry.fr,
          en: entry.en,
          es: entry.es,
          pt: entry.pt,
          targetValue: entry[targetLang] || entry.en || entry.fr,
          category: entry.category,
          note: entry.note,
          context_sensitive: entry.context_sensitive
        });
        break;
      }
    }
  }

  // Check archimonsters & wanted monsters (e.g., Maxi Malle, Aigripoil)
  for (const [frMon, enMon] of Object.entries(DOFUS_ARCHIMONSTERS_AND_WANTED)) {
    if (seen.has(frMon)) continue;
    const targetPattern = sourceLang === 'fr' ? frMon : enMon;
    const regex = new RegExp(`\\b${escapeRegExp(targetPattern)}\\b`, 'i');
    if (regex.test(lower)) {
      seen.add(frMon);
      found.push({
        source: targetPattern,
        fr: frMon.charAt(0).toUpperCase() + frMon.slice(1),
        en: enMon,
        category: 'monster',
        note: 'Monstre / Archi-monstre Dofus'
      });
    }
  }

  // Check dimensions and zones (e.g., Enutrosor -> Enurado)
  for (const [frZone, enZone] of Object.entries(DOFUS_DIMENSIONS_AND_ZONES)) {
    if (seen.has(frZone)) continue;
    const targetPattern = sourceLang === 'fr' ? frZone : enZone;
    const regex = new RegExp(`\\b${escapeRegExp(targetPattern)}\\b`, 'i');
    if (regex.test(lower)) {
      seen.add(frZone);
      found.push({
        source: targetPattern,
        fr: frZone.charAt(0).toUpperCase() + frZone.slice(1),
        en: enZone,
        category: 'zone',
        note: 'Dimension divine / Zone Dofus'
      });
    }
  }

  // Check classes & abbreviations (e.g., Roublard / roub -> Rogue)
  for (const [frClass, classData] of Object.entries(DOFUS_CLASSES_FR_EN)) {
    if (seen.has(frClass)) continue;
    const candidates = sourceLang === 'fr' ? [frClass, ...classData.short] : [classData.en];
    for (const cand of candidates) {
      const regex = new RegExp(`\\b${escapeRegExp(cand)}\\b`, 'i');
      if (regex.test(lower)) {
        seen.add(frClass);
        found.push({
          source: cand,
          fr: frClass.charAt(0).toUpperCase() + frClass.slice(1),
          en: classData.en,
          category: 'builds_and_classes',
          note: `Classe officielle Dofus (${classData.en})`
        });
        break;
      }
    }
  }

  return found.slice(0, 8);
}

function matchCase(source: string, target: string): string {
  if (source === source.toUpperCase()) return target.toUpperCase();
  if (source[0] === source[0].toUpperCase() && source.slice(1) === source.slice(1).toLowerCase()) {
    return target.charAt(0).toUpperCase() + target.slice(1);
  }
  return target;
}

function escapeRegExp(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
