import { escapeRegExp } from './constants';
import { MultiLangTokenRule } from './types';

export function createAchievementRegex(terms: string[]): RegExp {
  const termsPattern = terms.map(escapeRegExp).join('|');
  const prefix = '(?:succ[eéèê]s|achievements?|logros?|sucessos?)';
  const suffix = '(?:achievements?|succ[eéèê]s|logros?|sucessos?)';
  return new RegExp(
    `\\b(?:${prefix}\\s+(?:${termsPattern})(?:\\s+${suffix})?|(?:${termsPattern})\\s+${suffix}|(?:${termsPattern}))\\b`,
    'gi'
  );
}

export function createDoubleAchievementRegex(termsA: string[], termsB: string[]): RegExp {
  const patternA = termsA.map(escapeRegExp).join('|');
  const patternB = termsB.map(escapeRegExp).join('|');
  const prefix = '(?:succ[eéèê]s|achievements?|logros?|sucessos?)';
  const sep = '(?:\\s*(?:et|and|y|e|\\/|,|\\+)\\s*)';
  const suffix = '(?:achievements?|succ[eéèê]s|logros?|sucessos?)';
  return new RegExp(
    `\\b(?:${prefix}\\s+)?(?:${patternA})${sep}(?:${prefix}\\s+)?(?:${patternB})(?:\\s+${suffix})?\\b`,
    'gi'
  );
}

// Token rules mapped for all 4 languages (FR, EN, ES, PT)
export const MULTI_LANG_TOKEN_RULES: MultiLangTokenRule[] = [
  // Double Achievements combinations
  {
    pattern: createDoubleAchievementRegex(['hardi', 'impertinence', 'audaz'], ['collant', 'tight', 'pegajoso', 'grudado']),
    map: { fr: 'succès hardi et collant', en: 'Impertinence and Tight achievements', es: 'logros Audaz y Pegajoso', pt: 'sucessos Audaz e Pegajoso' }
  },
  {
    pattern: createDoubleAchievementRegex(['collant', 'tight', 'pegajoso', 'grudado'], ['hardi', 'impertinence', 'audaz']),
    map: { fr: 'succès collant et hardi', en: 'Tight and Impertinence achievements', es: 'logros Pegajoso y Audaz', pt: 'sucessos Pegajoso e Audaz' }
  },

  // Single Challenges & Achievements - bidirectional & strict official localizations
  {
    pattern: createAchievementRegex(['hardi', 'impertinence', 'audaz']),
    map: { fr: 'succès hardi', en: 'Impertinence achievement', es: 'logro Audaz', pt: 'sucesso Audaz' }
  },
  {
    pattern: createAchievementRegex(['collant', 'tight', 'pegajoso', 'grudado']),
    map: { fr: 'succès collant', en: 'Tight achievement', es: 'logro Pegajoso', pt: 'sucesso Pegajoso' }
  },
  {
    pattern: createAchievementRegex(['zombie', 'zombi', 'zumbi']),
    map: { fr: 'succès zombie', en: 'Zombie achievement', es: 'logro Zombi', pt: 'sucesso Zumbi' }
  },
  {
    pattern: createAchievementRegex(['statue', 'estatua', 'estátua']),
    map: { fr: 'succès statue', en: 'Statue achievement', es: 'logro Estatua', pt: 'sucesso Estátua' }
  },
  {
    pattern: createAchievementRegex(['premier', 'first', 'primero', 'primera posición', 'primeiro']),
    map: { fr: 'succès premier', en: 'First achievement', es: 'logro Primero', pt: 'sucesso Primeiro' }
  },
  {
    pattern: createAchievementRegex(['dernier', 'last', 'último', 'ultimo', 'última posición']),
    map: { fr: 'succès dernier', en: 'Last achievement', es: 'logro Último', pt: 'sucesso Último' }
  },
  {
    pattern: createAchievementRegex(['pusillanime', 'fainthearted', 'pusilánime', 'pusilanime', 'pusilânime']),
    map: { fr: 'succès pusillanime', en: 'Fainthearted achievement', es: 'logro Pusilánime', pt: 'sucesso Pusilânime' }
  },
  {
    pattern: createAchievementRegex(['nomade', 'nomad', 'nómada', 'nomada', 'nômade']),
    map: { fr: 'succès nomade', en: 'Nomad achievement', es: 'logro Nómada', pt: 'sucesso Nômade' }
  },
  {
    pattern: createAchievementRegex(['barbare', 'barbaric', 'bárbaro', 'barbaro']),
    map: { fr: 'succès barbare', en: 'Barbaric achievement', es: 'logro Bárbaro', pt: 'sucesso Bárbaro' }
  },
  {
    pattern: createAchievementRegex(['mystique', 'místico', 'mistico']),
    map: { fr: 'succès mystique', en: 'Mystique achievement', es: 'logro Místico', pt: 'sucesso Místico' }
  },
  {
    pattern: createAchievementRegex(['intouchable', 'untouchable', 'intocable', 'intocável', 'intocavel']),
    map: { fr: 'succès intouchable', en: 'Untouchable achievement', es: 'logro Intocable', pt: 'sucesso Intocável' }
  },
  {
    pattern: createAchievementRegex(['versatile', 'versátil', 'versatil']),
    map: { fr: 'succès versatile', en: 'Versatile achievement', es: 'logro Versátil', pt: 'sucesso Versátil' }
  },
  {
    pattern: createAchievementRegex(['blitzkrieg', 'blitz']),
    map: { fr: 'succès blitzkrieg', en: 'Blitzkrieg achievement', es: 'logro Blitzkrieg', pt: 'sucesso Blitzkrieg' }
  },
  {
    pattern: createAchievementRegex(['duo', 'dúo', 'dupla']),
    map: { fr: 'succès duo', en: 'Duo achievement', es: 'logro Dúo', pt: 'sucesso Duo' }
  },
  {
    pattern: createAchievementRegex(['trio', 'trío']),
    map: { fr: 'succès trio', en: 'Trio achievement', es: 'logro Trío', pt: 'sucesso Trio' }
  },
  {
    pattern: createAchievementRegex(['mains propres', 'main propre', 'clean hands', 'clean hand', 'manos limpias', 'mãos limpas', 'maos limpas']),
    map: { fr: 'succès mains propres', en: 'Clean Hands achievement', es: 'logro Manos limpias', pt: 'sucesso Mãos limpas' }
  },
  {
    pattern: createAchievementRegex(['anachorète', 'anachorete', 'misanthrope', 'hermit', 'anacoreta', 'misántropo', 'misantropo']),
    map: { fr: 'succès anachorète', en: 'Misanthrope achievement', es: 'logro Anacoreta', pt: 'sucesso Misantropo' }
  },
  {
    pattern: createAchievementRegex(['prudent', 'cautious', 'prudente']),
    map: { fr: 'succès prudent', en: 'Cautious achievement', es: 'logro Prudente', pt: 'sucesso Prudente' }
  },
  {
    pattern: createAchievementRegex(['élitiste', 'elitiste', 'elitist', 'elitista']),
    map: { fr: 'succès élitiste', en: 'Elitist achievement', es: 'logro Elitista', pt: 'sucesso Elitista' }
  },
  {
    pattern: createAchievementRegex(['focus', 'focalización', 'focalizacion', 'foco']),
    map: { fr: 'succès focus', en: 'Focus achievement', es: 'logro Focalización', pt: 'sucesso Foco' }
  },
  {
    pattern: createAchievementRegex(['circulez', 'keep moving', 'circulen', 'circulando']),
    map: { fr: 'succès circulez', en: 'Keep Moving achievement', es: 'logro ¡Circulen!', pt: 'sucesso Circulando!' }
  },
  {
    pattern: createAchievementRegex(['duel', 'duelo']),
    map: { fr: 'succès duel', en: 'Duel achievement', es: 'logro Duelo', pt: 'sucesso Duelo' }
  },
  {
    pattern: createAchievementRegex(['liberté', 'liberte', 'freedom', 'libertad', 'liberdade']),
    map: { fr: 'succès liberté', en: 'Freedom achievement', es: 'logro Libertad', pt: 'sucesso Liberdade' }
  },
  {
    pattern: createAchievementRegex(['économe', 'econome', 'scanty', 'ahorrador', 'econômico', 'economico']),
    map: { fr: 'succès économe', en: 'Scanty achievement', es: 'logro Ahorrador', pt: 'sucesso Econômico' }
  },
  {
    pattern: createAchievementRegex(['chrono', 'crono']),
    map: { fr: 'succès chrono', en: 'Chrono achievement', es: 'logro Crono', pt: 'sucesso Crono' }
  },
  {
    pattern: createAchievementRegex(['survivant', 'survivor', 'superviviente', 'sobrevivente']),
    map: { fr: 'succès survivant', en: 'Survivor achievement', es: 'logro Superviviente', pt: 'sucesso Sobrevivente' }
  },
  {
    pattern: createAchievementRegex(["deux pour le prix d'un", 'two for the price of one', 'el dos por uno', 'dois por um']),
    map: { fr: "succès deux pour le prix d'un", en: 'Two for the Price of One achievement', es: 'logro El dos por uno', pt: 'sucesso Dois por um' }
  },
  {
    pattern: createAchievementRegex(['partage', 'sharing', 'reparto', 'partilha']),
    map: { fr: 'succès partage', en: 'Sharing achievement', es: 'logro Reparto', pt: 'sucesso Partilha' }
  },

  // Stats & Damage
  {
    pattern: /\b(?:do\s+cri|critical\s+damage|da[ñn]os\s+cr[ií]ticos|danos\s+cr[ií]ticos)\b/gi,
    map: { fr: 'do cri', en: 'critical damage', es: 'daños críticos', pt: 'danos críticos' }
  },
  {
    pattern: /\b(?:do\s+pou|pushback\s+damage|da[ñn]os\s+(?:de\s+)?empuje|danos\s+(?:de\s+)?empurr[aã]o)\b/gi,
    map: { fr: 'do pou', en: 'pushback damage', es: 'daños de empuje', pt: 'danos de empurrão' }
  },
  {
    pattern: /\b(?:do\s+terre|earth\s+damage|da[ñn]os\s+(?:de\s+)?tierra|danos\s+(?:de\s+)?terra)\b/gi,
    map: { fr: 'do terre', en: 'earth damage', es: 'daños de tierra', pt: 'danos de terra' }
  },
  {
    pattern: /\b(?:do\s+feu|fire\s+damage|da[ñn]os\s+(?:de\s+)?fuego|danos\s+(?:de\s+)?fogo)\b/gi,
    map: { fr: 'do feu', en: 'fire damage', es: 'daños de fuego', pt: 'danos de fogo' }
  },
  {
    pattern: /\b(?:do\s+eau|water\s+damage|da[ñn]os\s+(?:de\s+)?agua|danos\s+(?:de\s+)?[aá]gua)\b/gi,
    map: { fr: 'do eau', en: 'water damage', es: 'daños de agua', pt: 'danos de água' }
  },
  {
    pattern: /\b(?:do\s+air|air\s+damage|da[ñn]os\s+(?:de\s+)?aire|danos\s+(?:de\s+)?ar)\b/gi,
    map: { fr: 'do air', en: 'air damage', es: 'daños de aire', pt: 'danos de ar' }
  },
  {
    pattern: /\b(?:do\s+neutre|neutral\s+damage|da[ñn]os\s+neutrales|danos\s+neutros)\b/gi,
    map: { fr: 'do neutre', en: 'neutral damage', es: 'daños neutrales', pt: 'danos neutros' }
  },
  {
    pattern: /\b(?:r[eéèê]sis?|res)\s+air\b/gi,
    map: { fr: 'résis air', en: 'air resistance', es: 'resistencia al aire', pt: 'resistência ao ar' }
  },
  {
    pattern: /\b(?:r[eéèê]sis?|res)\s+feu\b/gi,
    map: { fr: 'résis feu', en: 'fire resistance', es: 'resistencia al fuego', pt: 'resistência ao fogo' }
  },
  {
    pattern: /\b(?:r[eéèê]sis?|res)\s+eau\b/gi,
    map: { fr: 'résis eau', en: 'water resistance', es: 'resistencia al agua', pt: 'resistência à água' }
  },
  {
    pattern: /\b(?:r[eéèê]sis?|res)\s+terre\b/gi,
    map: { fr: 'résis terre', en: 'earth resistance', es: 'resistencia a la tierra', pt: 'resistência à terra' }
  },
  {
    pattern: /\b(?:r[eéèê]sis?|res)\s+neutre\b/gi,
    map: { fr: 'résis neutre', en: 'neutral resistance', es: 'resistencia neutral', pt: 'resistência neutra' }
  },
  {
    pattern: /\b(?:r[eéèê]sis|resis)\b/gi,
    map: { fr: 'résistances', en: 'resistances', es: 'resistencias', pt: 'resistências' }
  },

  // Runes, FM & Collectors
  {
    pattern: /\b(?:rune\s+)?ga\s+pme\b/gi,
    map: { fr: 'rune Ga Pme', en: 'MP rune', es: 'runa Ga Pme', pt: 'runa Ga Pme' }
  },
  {
    pattern: /\b(?:rune\s+)?ga\s+pa\b/gi,
    map: { fr: 'rune Ga Pa', en: 'AP rune', es: 'runa Ga Pa', pt: 'runa Ga Pa' }
  },
  {
    pattern: /\b(?:rune\s+)?pa\s+vi\b/gi,
    map: { fr: 'rune Pa Vi', en: 'Pa Vi rune', es: 'runa Pa Vi', pt: 'runa Pa Vi' }
  },
  {
    pattern: /\b(?:rune\s+)?ra\s+vi\b/gi,
    map: { fr: 'rune Ra Vi', en: 'Ra Vi rune', es: 'runa Ra Vi', pt: 'runa Ra Vi' }
  },
  {
    pattern: /\b(?:puits\s*pa|ap\s*sink|pozo\s*pa|po[çc]o\s*pa)\b/gi,
    map: { fr: 'puits PA', en: 'AP sink', es: 'pozo PA', pt: 'poço PA' }
  },
  {
    pattern: /\b(?:puits\s*pm|mp\s*sink|pozo\s*pm|po[çc]o\s*pm)\b/gi,
    map: { fr: 'puits PM', en: 'MP sink', es: 'pozo PM', pt: 'poço PM' }
  },
  {
    pattern: /\b(?:puits\s*po|range\s*sink|pozo\s*(?:de\s+)?alcance|po[çc]o\s*(?:de\s+)?alcance)\b/gi,
    map: { fr: 'puits PO', en: 'Range sink', es: 'pozo de alcance', pt: 'poço de alcance' }
  },
  {
    pattern: /\b(?:over\s*vita|vitality\s*over(?:mage)?)\b/gi,
    map: { fr: 'over vita', en: 'vitality overmage', es: 'over vita', pt: 'over vita' }
  },
  {
    pattern: /\b(?:jet\s+perf(?:ait)?|clean\s+roll|tirada\s+perfecta|rolagem\s+perfeita)\b/gi,
    map: { fr: 'jet parfait', en: 'clean roll', es: 'tirada perfecta', pt: 'rolagem perfeita' }
  },
  {
    pattern: /\b(?:forgemagie|smithmagic|forjamagia)\b/gi,
    map: { fr: 'forgemagie', en: 'smithmagic', es: 'forjamagia', pt: 'forjamagia' }
  },
  {
    pattern: /\b(?:d[eé]fense\s+perco(?:pteur)?|def\s+perco|perceptor\s+defense|defensa\s+(?:de\s+)?reca(?:udador)?|defesa\s+(?:de\s+)?coletor)\b/gi,
    map: { fr: 'défense percepteur', en: 'perceptor defense', es: 'defensa de recaudador', pt: 'defesa de coletor' }
  },
  {
    pattern: /\b(?:percepteurs?|perceptors?|recaudadores?|coletores?)\b/gi,
    map: { fr: 'percepteurs', en: 'perceptors', es: 'recaudadores', pt: 'coletores' }
  },
  {
    pattern: /\b(?:percepteur|perceptor|recaudador|coletor)\b/gi,
    map: { fr: 'percepteur', en: 'perceptor', es: 'recaudador', pt: 'coletor' }
  },

  // Combat Mechanics
  {
    pattern: /\b(?:tacle\s+et\s+fuite|fuite\s+et\s+tacle|lock\s+and\s+dodge|dodge\s+and\s+lock|placaje\s+y\s+huida|bloqueio\s+e\s+esquiva)\b/gi,
    map: { fr: 'tacle et fuite', en: 'lock and dodge', es: 'placaje y huida', pt: 'bloqueio e esquiva' }
  },
  {
    pattern: /\b(?:tacle|placaje|bloqueio)\b/gi,
    map: { fr: 'tacle', en: 'lock', es: 'placaje', pt: 'bloqueio' }
  },
  {
    pattern: /\b(?:fuite|huida|esquiva)\b/gi,
    map: { fr: 'fuite', en: 'dodge', es: 'huida', pt: 'esquiva' }
  },
  {
    pattern: /\b(?:pas\s+de\s+ldv|sans\s+ldv|no\s+line\s+of\s+sight|no\s+los|sin\s+l[ií]nea\s+de\s+visi[oó]n|sin\s+ldv|sem\s+linha\s+de\s+vis[aã]o|sem\s+ldv)\b/gi,
    map: { fr: 'pas de ligne de vue', en: 'no line of sight', es: 'sin línea de visión', pt: 'sem linha de visão' }
  },
  {
    pattern: /\b(?:ligne\s+de\s+vue|ldv|line\s+of\s+sight|l[ií]nea\s+de\s+visi[oó]n|linha\s+de\s+vis[aã]o)\b/gi,
    map: { fr: 'ligne de vue', en: 'line of sight', es: 'línea de visión', pt: 'linha de visão' }
  },
  {
    pattern: /\b(?:passe\s+(?:ton\s+)?tour|pass\s+turn|pasa\s+turno|passa\s+(?:a\s+)?vez)\b/gi,
    map: { fr: 'passe ton tour', en: 'pass turn', es: 'pasa turno', pt: 'passa a vez' }
  },
  {
    pattern: /\b(?:invu|invuln[eé]rable|invulnerable|invulner[aá]vel)\b/gi,
    map: { fr: 'invulnérable', en: 'invulnerable', es: 'invulnerable', pt: 'invulnerável' }
  },
  {
    pattern: /\b(?:insoignable|unhealable|incurable|incur[aá]vel)\b/gi,
    map: { fr: 'insoignable', en: 'unhealable', es: 'incurable', pt: 'incurável' }
  },
  {
    pattern: /\b(?:d[eé]buff|unbewitch|deshechizo|desencanto)\b/gi,
    map: { fr: 'débuff', en: 'unbewitch', es: 'deshechizo', pt: 'desencanto' }
  },

  // Avis de recherche & Quests
  {
    pattern: /\bavis\s+de\s+recherche\b/gi,
    map: { fr: 'avis de recherche', en: 'wanted notice', es: 'búsqueda y captura', pt: 'procurado' }
  },
  {
    pattern: /\b(?:les\s+avis|bounties|carteles\s+de\s+se\s+busca|procurados)\b/gi,
    map: { fr: 'avis de recherche', en: 'bounties', es: 'carteles de se busca', pt: 'procurados' }
  },
  {
    pattern: /\b(?:offrande\s+alma(?:nax)?|almanax\s+offering|ofrenda\s+del\s+almanax|oferenda\s+do\s+almanax)\b/gi,
    map: { fr: 'offrande Almanax', en: 'Almanax offering', es: 'ofrenda del Almanax', pt: 'oferenda do Almanax' }
  },
  {
    pattern: /\b(?:chasse\s+au(?:x)?\s+tr[eé]sors?|treasure\s+hunt|b[uú]squeda\s+de\s+tesoro|ca[çc]a\s+ao\s+tesouro)\b/gi,
    map: { fr: 'chasse au trésor', en: 'treasure hunt', es: 'búsqueda de tesoro', pt: 'caça ao tesouro' }
  },

  // Travel & Portals
  {
    pattern: /\b(?:pos\s+portail|portal\s+pos|pos\s+portal)\b/gi,
    map: { fr: 'pos portail', en: 'portal pos', es: 'pos portal', pt: 'pos portal' }
  },
  {
    pattern: /\b(?:havre[\s-]sac|mercasaco|saco\s+de\s+viagem|haven\s+bag)\b/gi,
    map: { fr: 'havre-sac', en: 'haven bag', es: 'mercasaco', pt: 'saco de viagem' }
  },

  // Dimensions
  {
    pattern: /\b(?:enutrosor|enurado|anutrop[ií]a)\b/gi,
    map: { fr: 'Enutrosor', en: 'Enurado', es: 'Anutropía', pt: 'Enutrosor' }
  },
  {
    pattern: /\b(?:srambad|sramvil)\b/gi,
    map: { fr: 'Srambad', en: 'Srambad', es: 'Sramvil', pt: 'Srambad' }
  },
  {
    pattern: /\b(?:x[eé]lorium)\b/gi,
    map: { fr: 'Xélorium', en: 'Xelorium', es: 'Xelorium', pt: 'Xelorium' }
  },
  {
    pattern: /\b(?:ecaflipus|[eé]caflipus|zurcalia)\b/gi,
    map: { fr: 'Ecaflipus', en: 'Ecaflipus', es: 'Zurcalia', pt: 'Ecaflipus' }
  },

  // Monstres & Familles de mobs (Dofus)
  // Ravageurs (Prevent translation to "pests" / "pest")
  {
    pattern: /\b(?:familles?\s+des?\s+ravageurs?|famille\s+ravageurs?|(?:the\s+)?destroyers?\s+family|familia\s+de\s+(?:los\s+)?devastadores|fam[ií]lia\s+dos?\s+devastadores)\b/gi,
    map: { fr: 'famille des Ravageurs', en: 'Destroyers family', es: 'familia de los Devastadores', pt: 'família dos Devastadores' }
  },
  {
    pattern: /\b(?:les\s+mobs?\s+ravageurs?|the\s+destroyer\s+mobs?|los\s+(?:mobs|monstruos)\s+devastadores|os\s+(?:mobs|monstros)\s+devastadores)\b/gi,
    map: { fr: 'les mobs Ravageurs', en: 'the Destroyer mobs', es: 'los monstruos devastadores', pt: 'os monstros devastadores' }
  },
  {
    pattern: /\b(?:mobs?\s+ravageurs?|destroyer\s+mobs?|monstruos\s+devastadores|monstros\s+devastadores)\b/gi,
    map: { fr: 'mobs Ravageurs', en: 'Destroyer mobs', es: 'monstruos devastadores', pt: 'monstros devastadores' }
  },
  {
    pattern: /\b(?:le\s+mob\s+ravageur|the\s+destroyer\s+mob|el\s+monstruo\s+devastador|o\s+monstro\s+devastador)\b/gi,
    map: { fr: 'le mob Ravageur', en: 'the Destroyer mob', es: 'el monstruo devastador', pt: 'o monstro devastador' }
  },
  {
    pattern: /\b(?:un\s+mob\s+ravageur|a\s+destroyer\s+mob|un\s+monstruo\s+devastador|um\s+monstro\s+devastador)\b/gi,
    map: { fr: 'un mob Ravageur', en: 'a Destroyer mob', es: 'un monstruo devastador', pt: 'um monstro devastador' }
  },
  {
    pattern: /\b(?:mob\s+ravageur|destroyer\s+mob|monstruo\s+devastador|monstro\s+devastador)\b/gi,
    map: { fr: 'mob Ravageur', en: 'Destroyer mob', es: 'monstruo devastador', pt: 'monstro devastador' }
  },
  {
    pattern: /\b(?:les\s+ravageurs|the\s+destroyers|los\s+devastadores|os\s+devastadores)\b/gi,
    map: { fr: 'les Ravageurs', en: 'the Destroyers', es: 'los devastadores', pt: 'os devastadores' }
  },
  {
    pattern: /\b(?:un\s+ravageur|a\s+destroyer|un\s+devastador|um\s+devastador)\b/gi,
    map: { fr: 'un Ravageur', en: 'a Destroyer', es: 'un devastador', pt: 'um devastador' }
  },
  {
    pattern: /\b(?:le\s+ravageur|the\s+destroyer|el\s+devastador|o\s+devastador)\b/gi,
    map: { fr: 'le Ravageur', en: 'the Destroyer', es: 'el devastador', pt: 'o devastador' }
  },

  // Key Dofus Monster Families
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+gloursons?|bearbarian\s+mobs?|the\s+bearbarians)\b/gi,
    map: { fr: 'les mobs Gloursons', en: 'the Bearbarian mobs', es: 'los monstruos golosotes', pt: 'os monstros ursóbaros' }
  },
  {
    pattern: /\b(?:les\s+gloursons|the\s+bearbarians|los\s+golosotes|os\s+urs[óo]baros)\b/gi,
    map: { fr: 'les Gloursons', en: 'the Bearbarians', es: 'los golosotes', pt: 'os ursóbaros' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+mansots?|pingwin\s+mobs?|the\s+pingwins)\b/gi,
    map: { fr: 'les mobs Mansots', en: 'the Pingwin mobs', es: 'los monstruos pájaros del tiempo', pt: 'os monstros pinguins' }
  },
  {
    pattern: /\b(?:les\s+mansots|the\s+pingwins|los\s+p[áa]jaros\s+del\s+tiempo|os\s+pinguins)\b/gi,
    map: { fr: 'les Mansots', en: 'the Pingwins', es: 'los pájaros del tiempo', pt: 'os pinguins' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+boufmouths?|mastogob\s+mobs?|the\s+mastogobs)\b/gi,
    map: { fr: 'les mobs Boufmouths', en: 'the Mastogob mobs', es: 'los monstruos jalamuts', pt: 'os monstros papatudos da neve' }
  },
  {
    pattern: /\b(?:les\s+boufmouths|the\s+mastogobs|los\s+jalamuts|os\s+papatudos\s+da\s+neve)\b/gi,
    map: { fr: 'les Boufmouths', en: 'the Mastogobs', es: 'los jalamuts', pt: 'os papatudos da neve' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+givrefoux|snowfoux\s+mobs?|the\s+snowfoux)\b/gi,
    map: { fr: 'les mobs Givrefoux', en: 'the Snowfoux mobs', es: 'los monstruos gélifux', pt: 'os monstros raposaneves' }
  },
  {
    pattern: /\b(?:les\s+givrefoux|the\s+snowfoux|los\s+g[ée]lifux|os\s+raposaneves)\b/gi,
    map: { fr: 'les Givrefoux', en: 'the Snowfoux', es: 'los gélifux', pt: 'os raposaneves' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+craqueleurs?|crackler\s+mobs?|the\s+cracklers)\b/gi,
    map: { fr: 'les mobs Craqueleurs', en: 'the Crackler mobs', es: 'los monstruos crujidores', pt: 'os monstros cracleres' }
  },
  {
    pattern: /\b(?:les\s+craqueleurs|the\s+cracklers|los\s+crujidores|os\s+cracleres)\b/gi,
    map: { fr: 'les Craqueleurs', en: 'the Cracklers', es: 'los crujidores', pt: 'os cracleres' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+abraknydes?|treechnid\s+mobs?|the\s+treechnids)\b/gi,
    map: { fr: 'les mobs Abraknydes', en: 'the Treechnid mobs', es: 'los monstruos abraknidos', pt: 'os monstros treechnids' }
  },
  {
    pattern: /\b(?:les\s+abraknydes|the\s+treechnids|los\s+abraknidos|os\s+treechnids)\b/gi,
    map: { fr: 'les Abraknydes', en: 'the Treechnids', es: 'los abraknidos', pt: 'os treechnids' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+mulous?|boowolf\s+mobs?|the\s+boowolves)\b/gi,
    map: { fr: 'les mobs Mulous', en: 'the Boowolf mobs', es: 'los monstruos mulus', pt: 'os monstros mulobos' }
  },
  {
    pattern: /\b(?:les\s+mulous|the\s+boowolves|los\s+mulus|os\s+mulobos)\b/gi,
    map: { fr: 'les Mulous', en: 'the Boowolves', es: 'los mulus', pt: 'os mulobos' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+dragoeufs?|dreggon\s+mobs?|the\s+dreggons)\b/gi,
    map: { fr: 'les mobs Dragoeufs', en: 'the Dreggon mobs', es: 'los monstruos dragohuevos', pt: 'os monstros dragovos' }
  },
  {
    pattern: /\b(?:les\s+dragoeufs|the\s+dreggons|los\s+dragohuevos|os\s+dragovos)\b/gi,
    map: { fr: 'les Dragoeufs', en: 'the Dreggons', es: 'los dragohuevos', pt: 'os dragovos' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+scarafeuilles?|scaraleaf\s+mobs?|the\s+scaraleaves)\b/gi,
    map: { fr: 'les mobs Scarafeuilles', en: 'the Scaraleaf mobs', es: 'los monstruos escarahojas', pt: 'os monstros escarafolhas' }
  },
  {
    pattern: /\b(?:les\s+scarafeuilles|the\s+scaraleaves|los\s+escarahojas|os\s+escarafolhas)\b/gi,
    map: { fr: 'les Scarafeuilles', en: 'the Scaraleaves', es: 'los escarahojas', pt: 'os escarafolhas' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+pious?|piwi\s+mobs?|the\s+piwis)\b/gi,
    map: { fr: 'les mobs Pious', en: 'the Piwi mobs', es: 'los monstruos píos', pt: 'os monstros pius' }
  },
  {
    pattern: /\b(?:les\s+pious|the\s+piwis|los\s+p[íi]os|os\s+pius)\b/gi,
    map: { fr: 'les Pious', en: 'the Piwis', es: 'los píos', pt: 'os pius' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+crocodailles?|crocodyl\s+mobs?|the\s+crocodyls)\b/gi,
    map: { fr: 'les mobs Crocodailles', en: 'the Crocodyl mobs', es: 'los monstruos cocodriluchos', pt: 'os monstros crocodilos' }
  },
  {
    pattern: /\b(?:les\s+crocodailles|the\s+crocodyls|los\s+cocodriluchos|os\s+crocodilos)\b/gi,
    map: { fr: 'les Crocodailles', en: 'the Crocodyls', es: 'los cocodriluchos', pt: 'os crocodilos' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+trithons?|tritun\s+mobs?|the\s+trituns)\b/gi,
    map: { fr: 'les mobs Trithons', en: 'the Tritun mobs', es: 'los monstruos tritones', pt: 'os monstros tritões' }
  },
  {
    pattern: /\b(?:les\s+trithons|the\s+trituns|los\s+tritones|os\s+trit[õo]es)\b/gi,
    map: { fr: 'les Trithons', en: 'the Trituns', es: 'los tritones', pt: 'os tritões' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+[eé]gar[eé]s?|fugitive\s+mobs?|the\s+fugitives)\b/gi,
    map: { fr: 'les mobs Égarés', en: 'the Fugitive mobs', es: 'los monstruos extraviados', pt: 'os monstros perdidos' }
  },
  {
    pattern: /\b(?:les\s+[eé]gar[eé]s|the\s+fugitives|los\s+extraviados|os\s+perdidos)\b/gi,
    map: { fr: 'les Égarés', en: 'the Fugitives', es: 'los extraviados', pt: 'os perdidos' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+gourgloutons?|glutton\s+mobs?|the\s+gluttons)\b/gi,
    map: { fr: 'les mobs Gourgloutons', en: 'the Glutton mobs', es: 'los monstruos tragaldabas', pt: 'os monstros gourgloutons' }
  },
  {
    pattern: /\b(?:les\s+gourgloutons|the\s+gluttons|los\s+tragaldabas|os\s+gourgloutons)\b/gi,
    map: { fr: 'les Gourgloutons', en: 'the Gluttons', es: 'los tragaldabas', pt: 'os gourgloutons' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+n[eé]cronyx|necronyx\s+mobs?|the\s+necronyx)\b/gi,
    map: { fr: 'les mobs Nécronyx', en: 'the Necronyx mobs', es: 'los monstruos necrónix', pt: 'os monstros necronyx' }
  },
  {
    pattern: /\b(?:les\s+n[eé]cronyx|the\s+necronyx|los\s+necr[óo]nix|os\s+necronyx)\b/gi,
    map: { fr: 'les Nécronyx', en: 'the Necronyx', es: 'los necrónix', pt: 'os necronyx' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+gel[eé]es?|jelly\s+mobs?|the\s+jellies)\b/gi,
    map: { fr: 'les mobs Gelées', en: 'the Jelly mobs', es: 'los monstruos gelatinas', pt: 'os monstros geléias' }
  },
  {
    pattern: /\b(?:les\s+gel[eé]es|the\s+jellies|las\s+gelatinas|as\s+gel[ée]ias)\b/gi,
    map: { fr: 'les Gelées', en: 'the Jellies', es: 'las gelatinas', pt: 'as geléias' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+porkass|lousy\s+pig\s+mobs?|the\s+lousy\s+pigs)\b/gi,
    map: { fr: 'les mobs Porkass', en: 'the Lousy Pig mobs', es: 'los monstruos porkass', pt: 'os monstros porkass' }
  },
  {
    pattern: /\b(?:les\s+porkass|the\s+lousy\s+pigs|los\s+porkass|os\s+porkass)\b/gi,
    map: { fr: 'les Porkass', en: 'the Lousy Pigs', es: 'los porkass', pt: 'os porkass' }
  },
  {
    pattern: /\b(?:(?:les\s+)?mobs?\s+kanigs?|kanig\s+mobs?|the\s+kanigs)\b/gi,
    map: { fr: 'les mobs Kanigs', en: 'the Kanig mobs', es: 'los monstruos kanigs', pt: 'os monstros kanigs' }
  },
  {
    pattern: /\b(?:les\s+kanigs|the\s+kanigs|los\s+kanigs|os\s+kanigs)\b/gi,
    map: { fr: 'les Kanigs', en: 'the Kanigs', es: 'los kanigs', pt: 'os kanigs' }
  },

  // Generic "mobs" and "familles de monstres" rules
  {
    pattern: /\b(?:familles?\s+de\s+(?:monstres?|mobs?)|monster\s+families|familias?\s+de\s+monstruos|fam[íi]lias?\s+de\s+monstros)\b/gi,
    map: { fr: 'familles de monstres', en: 'monster families', es: 'familias de monstruos', pt: 'famílias de monstros' }
  },
  {
    pattern: /\b(?:famille\s+de\s+(?:monstres?|mobs?)|monster\s+family|familia\s+de\s+monstruos|fam[íi]lia\s+de\s+monstros)\b/gi,
    map: { fr: 'famille de monstres', en: 'monster family', es: 'familia de monstruos', pt: 'família de monstros' }
  },
  {
    pattern: /\b(?:clean\s+les\s+mobs|clear\s+the\s+mobs|limpiar\s+los\s+(?:monstruos|mobs)|limpar\s+os\s+(?:monstros|mobs))\b/gi,
    map: { fr: 'clean les mobs', en: 'clear the mobs', es: 'limpiar los monstruos', pt: 'limpar os monstros' }
  },
  {
    pattern: /\b(?:pack\s+les\s+mobs|group\s+the\s+mobs|agrupar\s+los\s+monstruos|agrupar\s+os\s+monstros)\b/gi,
    map: { fr: 'pack les mobs', en: 'group the mobs', es: 'agrupar los monstruos', pt: 'agrupar os monstros' }
  },
  {
    pattern: /\b(?:bloque\s+le\s+mob|block\s+the\s+mob|bloquear\s+el\s+monstruo|bloquear\s+o\s+monstro)\b/gi,
    map: { fr: 'bloque le mob', en: 'block the mob', es: 'bloquea el monstruo', pt: 'bloqueia o monstro' }
  },
  {
    pattern: /\b(?:tacle\s+le\s+mob|lock\s+the\s+monster|placar\s+al\s+monstruo|travar\s+o\s+monstro)\b/gi,
    map: { fr: 'tacle le mob', en: 'lock the monster', es: 'placar al monstruo', pt: 'travar o monstro' }
  },
  {
    pattern: /\b(?:focus\s+le\s+mob|focus\s+the\s+monster|enfocar\s+al\s+monstruo|focar\s+(?:no|o)\s+monstro)\b/gi,
    map: { fr: 'focus le mob', en: 'focus the monster', es: 'enfocar al monstruo', pt: 'focar no monstro' }
  },
  {
    pattern: /\b(?:les\s+mobs|the\s+mobs|los\s+(?:mobs|monstruos)|os\s+(?:mobs|monstros))\b/gi,
    map: { fr: 'les mobs', en: 'the mobs', es: 'los monstruos', pt: 'os monstros' }
  },
  {
    pattern: /\b(?:le\s+mob|the\s+mob|el\s+(?:mob|monstruo)|o\s+(?:mob|monstro))\b/gi,
    map: { fr: 'le mob', en: 'the mob', es: 'el monstruo', pt: 'o monstro' }
  },
  {
    pattern: /\b(?:un\s+mob|a\s+mob|un\s+monstruo|um\s+monstro)\b/gi,
    map: { fr: 'un mob', en: 'a mob', es: 'un monstruo', pt: 'um monstro' }
  },
  {
    pattern: /\b(?:des\s+mobs)\b/gi,
    map: { fr: 'des mobs', en: 'mobs', es: 'monstruos', pt: 'monstros' }
  },

  // Combat range & CAC
  {
    pattern: /\b(?:attention|gaffe)\s+au\s+(?:cac|corps[- ]à[- ]corps)\b/gi,
    map: { fr: 'attention au CAC', en: 'watch out for melee', es: 'cuidado con el cuerpo a cuerpo', pt: 'cuidado com o combate corpo a corpo' }
  },
  {
    pattern: /\b(?:au\s+cac|au\s+corps[- ]à[- ]corps|en\s+cuerpo\s+a\s+cuerpo|em\s+combate\s+corpo\s+a\s+corpo)\b/gi,
    map: { fr: 'au CAC', en: 'in melee', es: 'en cuerpo a cuerpo', pt: 'em combate corpo a corpo' }
  },
  {
    pattern: /\b(?:zone\s+cac|zone\s+corps[- ]à[- ]corps)\b/gi,
    map: { fr: 'zone CAC', en: 'melee range', es: 'zona cuerpo a cuerpo', pt: 'alcance corpo a corpo' }
  },
  {
    pattern: /\b(?:arme\s+(?:de\s+)?cac|arme\s+(?:de\s+)?corps[- ]à[- ]corps)\b/gi,
    map: { fr: 'arme de CAC', en: 'melee weapon', es: 'arma cuerpo a cuerpo', pt: 'arma de combate corpo a corpo' }
  },

  // Technical & Reconnection
  {
    pattern: /\b(?:mon\s+jeu\s+a\s+plant[eé][,\s]+je\s+me\s+reconnecte|mi\s+juego\s+se\s+cerr[oó][,\s]+reconectando|meu\s+jogo\s+travou[,\s]+reconectando)\b/gi,
    map: { fr: 'mon jeu a planté, je me reconnecte', en: 'my game crashed, reconnecting', es: 'mi juego se cerró, reconectando', pt: 'meu jogo travou, reconectando' }
  },
  {
    pattern: /\b(?:mon\s+jeu\s+a\s+plant[eé]|mi\s+juego\s+se\s+cerr[oó]|meu\s+jogo\s+travou)\b/gi,
    map: { fr: 'mon jeu a planté', en: 'my game crashed', es: 'mi juego se cerró', pt: 'meu jogo travou' }
  },
  {
    pattern: /\b(?:je\s+me\s+reconnecte|reconectando)\b/gi,
    map: { fr: 'je me reconnecte', en: 'reconnecting', es: 'reconectando', pt: 'reconectando' }
  },

  // Boss recruitment shortcuts
  {
    pattern: /\bqui\s+(?:veut\s+faire|pour)\s+(?:un\s+|le\s+)?(?:dc|Dragon\s+Cochon)\b/gi,
    map: { fr: 'qui veut faire un Dragon Cochon ?', en: 'who wants to do a Dragon Pig?', es: '¿quién quiere hacer un Dragocerdo?', pt: 'quem quer fazer um Dragão-Porco?' }
  },
  {
    pattern: /\bqui\s+(?:veut\s+faire|pour)\s+(?:un\s+|le\s+)?(?:rm|Royalmouth)\b/gi,
    map: { fr: 'qui veut faire un Royalmouth ?', en: 'who wants to do a Royal Mastogob?', es: '¿quién quiere hacer un Jalamut Real?', pt: 'quem quer fazer um Papatudo da Neve Real?' }
  },
  {
    pattern: /\bqui\s+(?:veut\s+faire|pour)\s+(?:un\s+|le\s+)?(?:br|Bouftou\s+Royal)\b/gi,
    map: { fr: 'qui veut faire un Bouftou Royal ?', en: 'who wants to do a Royal Gobball?', es: '¿quién quiere hacer un Jalató Real?', pt: 'quem quer fazer um Papatudo Real?' }
  },
  {
    pattern: /\bqui\s+(?:veut\s+faire|pour)\s+(?:un\s+|le\s+)?(?:cm|Chêne\s+Mou)\b/gi,
    map: { fr: 'qui veut faire un Chêne Mou ?', en: 'who wants to do a Soft Oak?', es: '¿quién quiere hacer un Roble Blando?', pt: 'quem quer fazer um Carvalho Mole?' }
  },
  {
    pattern: /\bqui\s+(?:veut\s+(?:combattre|faire)|pour\s+taper|pour)\s+(?:un\s+|le\s+)?(?:gourlo[t]?|Gourlo\s+le\s+Terrible)\b/gi,
    map: { fr: 'qui veut faire Gourlo le Terrible ?', en: 'who wants to fight Gourlo the Terrible?', es: '¿quién quiere combatir a Gourlo el Terrible?', pt: 'quem quer combater Gourlo, o Terrível?' }
  },

  // Recruitment & Common Idioms (4 languages)
  {
    pattern: /(?:^|\b)(?:qui\s+est\s+chaud\s+pour|who\s+is\s+down\s+for|qui[eé]n\s+(?:se\s+apunta\s+a|para)|quem\s+topa)\b/gi,
    map: { fr: 'qui est chaud pour', en: 'who is down for', es: 'quién se apunta a', pt: 'quem topa' }
  },
  {
    pattern: /(?:^|\b)(?:qui\s+est\s+chaud|who\s+is\s+down|qui[eé]n\s+se\s+apunta|quem\s+topa)\b/gi,
    map: { fr: 'qui est chaud', en: 'who is down', es: 'quién se apunta', pt: 'quem topa' }
  },
  {
    pattern: /(?:^|\b)(?:qui\s+g[eéèê]re|who\s+can\s+carry|qui[eé]n\s+(?:puede\s+pasar|pasa)|quem\s+(?:consegue\s+passar|passa))\b/gi,
    map: { fr: 'qui gère', en: 'who can carry', es: 'quién puede pasar', pt: 'quem consegue passar' }
  },
  {
    pattern: /(?:^|\b)(?:tu\s+g[eéèê]res|can\s+you\s+carry|puedes\s+pasar|consegue\s+passar)\b/gi,
    map: { fr: 'tu gères', en: 'can you carry', es: 'puedes pasar', pt: 'consegue passar' }
  },
  {
    pattern: /(?:^|\b)(?:tu\s+peux|peux\s+tu)\s+(?:g[eéèê]rer|carry)\b/gi,
    map: { fr: 'tu peux gérer', en: 'can you carry', es: 'puedes pasar', pt: 'consegue passar' }
  },
  {
    pattern: /(?:^|\b)(?:je\s+g[eéèê]re|i\s+can\s+carry|puedo\s+pasar|consigo\s+passar)\b/gi,
    map: { fr: 'je gère', en: 'I can carry', es: 'puedo pasar', pt: 'consigo passar' }
  },
  {
    pattern: /(?:^|\b)(?:je\s+peux)\s+(?:g[eéèê]rer|carry)\b/gi,
    map: { fr: 'je peux gérer', en: 'I can carry', es: 'puedo pasar', pt: 'consigo passar' }
  },
  {
    pattern: /\b(?:mp\s+moi|[pd]m\s+me|env[ií]ame\s+mp|manda\s+mp)\b/gi,
    map: { fr: 'mp moi', en: 'DM me', es: 'envíame mp', pt: 'manda mp' }
  },
  {
    pattern: /\b(?:mp\s+offre|[pd]m\s+offer|mp\s+oferta)\b/gi,
    map: { fr: 'mp offre', en: 'DM offer', es: 'mp oferta', pt: 'mp oferta' }
  },
  {
    pattern: /\b(?:1\s+place|1\s+spot|1\s+plaza|1\s+vaga)\b/gi,
    map: { fr: '1 place', en: '1 spot', es: '1 plaza', pt: '1 vaga' }
  },
  {
    pattern: /\b(\d+)\s+(?:places?|spots?|plazas?|vagas?)\b/gi,
    map: (_match: string, n: string) => {
      const num = Number(n);
      return {
        fr: `${num} place${num > 1 ? 's' : ''}`,
        en: `${num} spot${num > 1 ? 's' : ''}`,
        es: `${num} plaza${num > 1 ? 's' : ''}`,
        pt: `${num} vaga${num > 1 ? 's' : ''}`
      };
    }
  },
  {
    pattern: /\bspots\b/gi,
    map: { fr: 'places', en: 'spots', es: 'plazas', pt: 'vagas' }
  },
  {
    pattern: /\b(?:derni[eè]re\s+place|last\s+spot|[uú]ltima\s+plaza|[uú]ltima\s+vaga)\b/gi,
    map: { fr: 'dernière place', en: 'last spot', es: 'última plaza', pt: 'última vaga' }
  },
  {
    pattern: /(?:^|\b)(?:LF|LFG)\b/g,
    map: { fr: 'cherche', en: 'LF', es: 'busco', pt: 'procuro' }
  },
  {
    pattern: /\b(?:LF|LFG|LFM)\s*1\s*M\b/gi,
    map: { fr: 'cherche 1 joueur', en: 'LF 1 player', es: 'busco 1 jugador', pt: 'procuro 1 jogador' }
  },
  {
    pattern: /\b(?:LF|LFG|LFM)\s*2\s*M\b/gi,
    map: { fr: 'cherche 2 joueurs', en: 'LF 2 players', es: 'busco 2 jugadores', pt: 'procuro 2 jogadores' }
  },
  {
    pattern: /\b(?:LF|LFG|LFM)\s*(\d+)\s*M\b/gi,
    map: (_match: string, n: string) => ({
      fr: `cherche ${n} joueurs`,
      en: `LF ${n} players`,
      es: `busco ${n} jugadores`,
      pt: `procuro ${n} jogadores`
    })
  },
  {
    pattern: /\b(?:LF|LFG|LFM)\s+group\b/gi,
    map: { fr: 'cherche groupe', en: 'LF group', es: 'busco grupo', pt: 'procuro grupo' }
  },
  {
    pattern: /\b(?:busco\s+grupo|procuro\s+grupo)\b/gi,
    map: { fr: 'cherche groupe', en: 'LF group', es: 'busco grupo', pt: 'procuro grupo' }
  },
  {
    pattern: /\b(?:places?\s+restantes?|spots?\s+left|plazas?\s+restantes?|vagas?\s+restantes?)\b/gi,
    map: { fr: 'places restantes', en: 'spots left', es: 'plazas restantes', pt: 'vagas restantes' }
  },
  {
    pattern: /\b(?:exo\s*pa|ap\s*exo)\b/gi,
    map: { fr: 'exo PA', en: 'AP exo', es: 'exo PA', pt: 'exo PA' }
  },
  {
    pattern: /\b(?:exo\s*pm|mp\s*exo)\b/gi,
    map: { fr: 'exo PM', en: 'MP exo', es: 'exo PM', pt: 'exo PM' }
  },
  {
    pattern: /\b(?:exo\s*po|range\s*exo|exo\s*alcance)\b/gi,
    map: { fr: 'exo PO', en: 'range exo', es: 'exo alcance', pt: 'exo alcance' }
  },
  {
    pattern: /\b(?:pano(?:plie)?\s+sasa|wisdom\s+set|set\s+de\s+sabidur[ií]a|conjunto\s+de\s+sabedoria)\b/gi,
    map: { fr: 'panoplie sagesse', en: 'wisdom set', es: 'set de sabiduría', pt: 'conjunto de sabedoria' }
  },
  {
    pattern: /\b(?:pano(?:plie)?\s+pp|prospecting\s+set|set\s+de\s+prospecci[oó]n|conjunto\s+de\s+prospec[çc][aã]o)\b/gi,
    map: { fr: 'panoplie prospection', en: 'prospecting set', es: 'set de prospección', pt: 'conjunto de prospecção' }
  },
  {
    pattern: /\b(?:prix\s+fixe|prix\s+ferme|firm\s+price|precio\s+fijo|pre[çc]o\s+fixo|no\s+n[eé]go)\b/gi,
    map: { fr: 'prix ferme', en: 'firm price', es: 'precio fijo', pt: 'preço fixo' }
  },
  {
    pattern: /\b(?:achat\s+revente|buying\s+&\s+reselling|compra\s+y\s+reventa|compra\s+e\s+revenda)\b/gi,
    map: { fr: 'achat revente', en: 'buying & reselling', es: 'compra y reventa', pt: 'compra e revenda' }
  },
  {
    pattern: /\b(?:sauvegarde\s+boss|saved\s+at\s+boss|guardado\s+en\s+boss|salvo\s+no\s+boss)\b/gi,
    map: { fr: 'sauvegarde boss', en: 'saved at boss', es: 'guardado en boss', pt: 'salvo no boss' }
  },
  {
    pattern: /\b(?:passage\s+donjon|passage\s+dj|dungeon\s+carry|pase\s+de\s+mazmorra|passagem\s+de\s+calabou[çc]o)\b/gi,
    map: { fr: 'passage donjon', en: 'dungeon carry', es: 'pase de mazmorra', pt: 'passagem de calabouço' }
  },
  {
    pattern: /\b(?:passeur|carregador|pasador)\b/gi,
    map: { fr: 'passeur', en: 'carry', es: 'pasador', pt: 'carregador' }
  },
  {
    pattern: /\b(?:speed\s+farmin?g?)\b/gi,
    map: { fr: 'speed farm', en: 'speed farm', es: 'speed farm', pt: 'speed farm' }
  },
  {
    pattern: /\b(?:songes\s+infinis?|infinite\s+dreams?|sue[ñn]os\s+infinitos?|sonhos\s+infinitos?)\b/gi,
    map: { fr: 'Songes Infinis', en: 'Infinite Dreams', es: 'Sueños Infinitos', pt: 'Sonhos Infinitos' }
  },
  {
    pattern: /\b(?:songes?\s+[eé]tage\s*(\d+)|infinite\s+dreams?\s+floor\s*(\d+)|sue[ñn]os?\s+piso\s*(\d+)|sonhos?\s+andar\s*(\d+))\b/gi,
    map: (_match: string, p1: string, p2: string, p3: string, p4: string) => {
      const floor = p1 || p2 || p3 || p4;
      return {
        fr: `Songes étage ${floor}`,
        en: `Infinite Dreams floor ${floor}`,
        es: `Sueños piso ${floor}`,
        pt: `Sonhos andar ${floor}`
      };
    }
  },
  {
    pattern: /\b(?:pierres?\s+d['’]âme|soul\s+stones?|piedras?\s+de\s+alma|pedras?\s+de\s+alma)\b/gi,
    map: { fr: "pierre d'âme", en: 'soul stone', es: 'piedra de alma', pt: 'pedra de alma' }
  },
  {
    pattern: /\b(?:archimonstres?|archmonsters?|archimonstruos?|arquimonstros?)\b/gi,
    map: { fr: 'archimonstre', en: 'archmonster', es: 'archimonstruo', pt: 'arquimonstro' }
  },

  // Gaming invitations: "ça te dit ?", "qui veut faire X ?"
  {
    pattern: /(?<=^|[\s,.;:!?])(?:ça|ca|sa)\s+vous\s+dit\s+(?:un\s+|une\s+|le\s+|la\s+|les\s+|des\s+|de\s+faire\s+un\s+|de\s+faire\s+)?(.+?)\s*\?/gi,
    map: (_match: string, p1: string) => ({
      fr: `ça vous dit ${p1} ?`,
      en: `are you guys down for ${p1}?`,
      es: `¿os apetece ${p1}?`,
      pt: `vocês topam ${p1}?`
    })
  },
  {
    pattern: /(?<=^|[\s,.;:!?])(?:ça|ca|sa)\s+te\s+dit\s+(?:un\s+|une\s+|le\s+|la\s+|les\s+|des\s+|de\s+faire\s+un\s+|de\s+faire\s+)?(.+?)\s*\?/gi,
    map: (_match: string, p1: string) => ({
      fr: `ça te dit ${p1} ?`,
      en: `are you down for ${p1}?`,
      es: `¿te apetece ${p1}?`,
      pt: `você topa ${p1}?`
    })
  },
  {
    pattern: /(?<=^|[\s,.;:!?])(?:ça|ca|sa)\s+te\s+dit(?:\s*\?|\b|$)/gi,
    map: { fr: 'ça te dit ?', en: 'are you down?', es: '¿te apetece?', pt: 'você topa?' }
  },
  {
    pattern: /(?<=^|[\s,.;:!?])(?:ça|ca|sa)\s+vous\s+dit(?:\s*\?|\b|$)/gi,
    map: { fr: 'ça vous dit ?', en: 'are you guys down?', es: '¿os apetece?', pt: 'vocês topam?' }
  },
  {
    pattern: /(?<=^|[\s,.;:!?])(?:ça|ca|sa)\s+te\s+tente(?:\s*\?|\b|$)/gi,
    map: { fr: 'ça te tente ?', en: 'are you up for it?', es: '¿te tienta?', pt: 'você topa?' }
  },
  {
    pattern: /(?<=^|[\s,.;:!?])(?:ça|ca|sa)\s+vous\s+tente(?:\s*\?|\b|$)/gi,
    map: { fr: 'ça vous tente ?', en: 'are you guys up for it?', es: '¿os tienta?', pt: 'vocês topam?' }
  },

  // Combat spells & tactics (one-shot, libé, coop, corrup, clean adds)
  {
    pattern: /\b(?:one[- ]shot\s+le\s+monstre|one[- ]shot\s+the\s+monster|derrotar\s+de\s+un\s+golpe\s+al\s+monstruo|derrotar\s+de\s+um\s+golpe\s+o\s+monstro)\b/gi,
    map: { fr: 'one-shot le monstre', en: 'one-shot the monster', es: 'derrotar de un golpe al monstruo', pt: 'derrotar de um golpe o monstro' }
  },
  {
    pattern: /\b(?:one[- ]shot\s+les\s+monstres|one[- ]shot\s+the\s+monsters|derrotar\s+de\s+un\s+golpe\s+a\s+los\s+monstruos|derrotar\s+de\s+um\s+golpe\s+os\s+monstros)\b/gi,
    map: { fr: 'one-shot les monstres', en: 'one-shot the monsters', es: 'derrotar de un golpe a los monstruos', pt: 'derrotar de um golpe os monstros' }
  },
  {
    pattern: /\b(?:lance\s+Lib[eé]ration\s+sur\s+le\s+monstre|cast\s+Release\s+on\s+the\s+monster|usa\s+Liberaci[oó]n\s+sobre\s+el\s+monstruo|use\s+Libera[çc][aã]o\s+no\s+monstro)\b/gi,
    map: { fr: 'lance Libération sur le monstre', en: 'cast Release on the monster', es: 'usa Liberación sobre el monstruo', pt: 'use Liberação no monstro' }
  },
  {
    pattern: /\b(?:lance\s+Coop[eé]ration\s+sur\s+le\s+monstre|cast\s+Cooperation\s+on\s+the\s+monster|usa\s+Cooperaci[oó]n\s+sobre\s+el\s+monstruo|use\s+Coopera[çc][aã]o\s+no\s+monstro)\b/gi,
    map: { fr: 'lance Coopération sur le monstre', en: 'cast Cooperation on the monster', es: 'usa Cooperación sobre el monstruo', pt: 'use Cooperação no monstro' }
  },
  {
    pattern: /\b(?:lance\s+Corruption\s+sur\s+le\s+boss|cast\s+Corruption\s+on\s+the\s+boss|cast\s+Bribery\s+on\s+the\s+boss|usa\s+Corrupci[oó]n\s+sobre\s+el\s+boss|use\s+Corrup[çc][aã]o\s+no\s+chefe)\b/gi,
    map: { fr: 'lance Corruption sur le boss', en: 'cast Bribery on the boss', es: 'usa Corrupción sobre el boss', pt: 'use Corrupção no chefe' }
  },
  {
    pattern: /\b(?:nettoie\s+les\s+monstres\s+secondaires|clean\s+the\s+adds|clear\s+the\s+adds|limpia\s+los\s+esbirros|limpe\s+os\s+lacaios)\b/gi,
    map: { fr: 'nettoie les monstres secondaires', en: 'clear the adds', es: 'limpia los esbirros', pt: 'limpe os lacaios' }
  },
  {
    pattern: /\b(?:tue\s+les\s+monstres\s+secondaires|kill\s+the\s+adds|mata\s+los\s+esbirros|mate\s+os\s+lacaios)\b/gi,
    map: { fr: 'tue les monstres secondaires', en: 'kill the adds', es: 'mata los esbirros', pt: 'mate os lacaios' }
  },

  // Range & Combat mechanics (PO, PM, PA, States)
  {
    pattern: /\b(?:pas\s+assez\s+de\s+port[eé]e|manque\s+de\s+port[eé]e|not\s+enough\s+range|lack\s+of\s+range|falta\s+de\s+alcance)\b/gi,
    map: { fr: 'pas assez de portée', en: 'not enough range', es: 'falta de alcance', pt: 'falta de alcance' }
  },
  {
    pattern: /\b(?:hors\s+de\s+port[eé]e|out\s+of\s+range|fuera\s+de\s+alcance|fora\s+de\s+alcance)\b/gi,
    map: { fr: 'hors de portée', en: 'out of range', es: 'fuera de alcance', pt: 'fora de alcance' }
  },
  {
    pattern: /\b(?:retrait\s+PM|MP\s+reduction|reducci[oó]n\s+de\s+PM|redu[çc][aã]o\s+de\s+PM)\b/gi,
    map: { fr: 'retrait PM', en: 'MP reduction', es: 'reducción de PM', pt: 'redução de PM' }
  },
  {
    pattern: /\b(?:retrait\s+PA|AP\s+reduction|reducci[oó]n\s+de\s+PA|redu[çc][aã]o\s+de\s+PA)\b/gi,
    map: { fr: 'retrait PA', en: 'AP reduction', es: 'reducción de PA', pt: 'redução de PA' }
  },
  {
    pattern: /\b(?:[eé]tat\s+invuln[eé]rable|invulnerable\s+state|estado\s+invulnerable|estado\s+invulner[aá]vel)\b/gi,
    map: { fr: 'état invulnérable', en: 'Invulnerable state', es: 'estado invulnerable', pt: 'estado invulnerável' }
  },
  {
    pattern: /\b(?:[eé]tat\s+pesenteur|heavy\s+state|gravity\s+state|estado\s+pesado)\b/gi,
    map: { fr: 'état pesenteur', en: 'Heavy state', es: 'estado pesado', pt: 'estado pesado' }
  },
  {
    pattern: /\b(?:[eé]tat\s+insoignable|unhealable\s+state|incurable\s+state|estado\s+incurable|estado\s+incur[aá]vel)\b/gi,
    map: { fr: 'état insoignable', en: 'Unhealable state', es: 'estado incurable', pt: 'estado incurável' }
  },
  {
    pattern: /\b(?:reste\s+à\s+distance\s+de\s+|stay\s+away\s+from\s+|mantente\s+alejado\s+de\s+|fique\s+longe\s+de\s+)\b/gi,
    map: { fr: 'reste à distance de ', en: 'stay away from ', es: 'mantente alejado de ', pt: 'fique longe de ' }
  },

  // Item sets ("panoplie")
  {
    pattern: /\b(?:panoplie\s+Bouftou\s+Royal|royal\s+gobball\s+set|set\s+de\s+jalat[oó]\s+real|conjunto\s+de\s+papatudo\s+real)\b/gi,
    map: { fr: 'panoplie Bouftou Royal', en: 'Royal Gobball set', es: 'set de Jalató Real', pt: 'conjunto de Papatudo Real' }
  },
  {
    pattern: /\b(?:panoplie\s+Bouftou|gobball\s+set|set\s+de\s+jalat[oó]|conjunto\s+de\s+papatudo)\b/gi,
    map: { fr: 'panoplie Bouftou', en: 'Gobball set', es: 'set de Jalató', pt: 'conjunto de Papatudo' }
  },
  {
    pattern: /\b(?:panoplie\s+Meulou|moowolf\s+set|set\s+de\s+maxilubo|conjunto\s+de\s+mulobo)\b/gi,
    map: { fr: 'panoplie Meulou', en: 'Moowolf set', es: 'set de Maxilubo', pt: 'conjunto de Mulobo' }
  },
  {
    pattern: /\b(?:panoplie\s+Ch[eê]ne\s+Mou|soft\s+oak\s+set|set\s+de\s+roble\s+blando|conjunto\s+de\s+carvalho\s+mole)\b/gi,
    map: { fr: 'panoplie Chêne Mou', en: 'Soft Oak set', es: 'set de Roble Blando', pt: 'conjunto de Carvalho Mole' }
  },
  {
    pattern: /\b(?:panoplie\s+Piou|piwi\s+set|set\s+de\s+p[ií]o|conjunto\s+de\s+piu)\b/gi,
    map: { fr: 'panoplie Piou', en: 'Piwi set', es: 'set de Pío', pt: 'conjunto de Piu' }
  },
  {
    pattern: /\b(?:combien\s+la\s+panoplie\s+Bouftou\s+Royal|how\s+much\s+for\s+the\s+royal\s+gobball\s+set)\b/gi,
    map: { fr: 'combien la panoplie Bouftou Royal ?', en: 'how much for the Royal Gobball set?', es: '¿cuánto por el set de Jalató Real?', pt: 'quanto custa o conjunto de Papatudo Real?' }
  },
  {
    pattern: /\b(?:combien\s+la\s+panoplie\s+Bouftou|how\s+much\s+for\s+the\s+gobball\s+set)\b/gi,
    map: { fr: 'combien la panoplie Bouftou ?', en: 'how much for the Gobball set?', es: '¿cuánto por el set de Jalató?', pt: 'quanto custa o conjunto de Papatudo?' }
  },
  {
    pattern: /\b(?:combien\s+la\s+panoplie\s+([a-zA-ZÀ-ÿ\s]+?)\s*\?)/gi,
    map: (_match: string, p1: string) => ({
      fr: `combien la panoplie ${p1} ?`,
      en: `how much for the ${p1} set?`,
      es: `¿cuánto por el set ${p1}?`,
      pt: `quanto custa o conjunto ${p1}?`
    })
  },

  // Social & Travel (meet at zaap, tp donjon, keyring, etc.)
  {
    pattern: /\b(?:qui\s+a\s+le\s+trousseau(?:\s+de\s+clefs?)?\s*\?|who\s+has\s+the\s+keyring\s*\?|¿?qui[eé]n\s+tiene\s+el\s+manojo\s+de\s+llaves\s*\?|quem\s+tem\s+o\s+chaveiro\s*\?)\b/gi,
    map: { fr: 'qui a le trousseau de clefs ?', en: 'who has the keyring?', es: '¿quién tiene el manojo de llaves?', pt: 'quem tem o chaveiro?' }
  },
  {
    pattern: /\b(?:allons\s+au\s+zaap|let\'?s\s+go\s+to\s+(?:the\s+)?zaap|vamos\s+al\s+zaap(?:\s+de)?|vamos\s+ao\s+zaap(?:\s+de)?)\s+([a-zA-ZÀ-ÿ]+)/gi,
    map: (_match: string, p1: string) => ({
      fr: `allons au zaap ${p1}`,
      en: `let's go to ${p1} zaap`,
      es: `vamos al zaap de ${p1}`,
      pt: `vamos ao zaap de ${p1}`
    })
  },
  {
    pattern: /\b(?:sauvegarde\s+au\s+zaap|save\s+at\s+(?:the\s+)?zaap|guarda\s+en\s+el\s+zaap(?:\s+de)?|salve\s+no\s+zaap(?:\s+de)?)\s+([a-zA-ZÀ-ÿ]+)/gi,
    map: (_match: string, p1: string) => ({
      fr: `sauvegarde au zaap ${p1}`,
      en: `save at ${p1} zaap`,
      es: `guarda en el zaap de ${p1}`,
      pt: `salve no zaap de ${p1}`
    })
  },
  {
    pattern: /\b(?:tranquille\s+on\s+g[eé]re|no\s+worries[,\s]+we\s+got\s+this|tranquilo[,\s]+lo\s+tenemos\s+bajo\s+control|tranquilo[,\s]+a\s+gente\s+consegue)\b/gi,
    map: { fr: 'tranquille on gère', en: 'no worries, we got this', es: 'tranquilo, lo tenemos bajo control', pt: 'tranquilo, a gente consegue' }
  },
  {
    pattern: /\b(?:invite\s+s\'il\s+te\s+pla[iî]t|invite\s+please|invita\s+por\s+favor|convida\s+por\s+favor)\b/gi,
    map: { fr: "invite s'il te plaît", en: 'invite please', es: 'invita por favor', pt: 'convida por favor' }
  },
  {
    pattern: /\b(?:rendez[- ]vous\s+au\s+zaap|meet\s+at\s+(?:the\s+)?zaap|reuni[oó]n\s+en\s+el\s+zaap|encontro\s+no\s+zaap)\b/gi,
    map: { fr: 'rendez-vous au zaap', en: 'meet at the zaap', es: 'reunión en el zaap', pt: 'encontro no zaap' }
  },
  {
    pattern: /\b(?:rendez[- ]vous\s+devant\s+le\s+donjon|meet\s+in\s+front\s+of\s+the\s+dungeon|reuni[oó]n\s+frente\s+a\s+la\s+mazmorra|encontro\s+na\s+frente\s+do\s+calabou[çc]o)\b/gi,
    map: { fr: 'rendez-vous devant le donjon', en: 'meet in front of the dungeon', es: 'reunión frente a la mazmorra', pt: 'encontro na frente do calabouço' }
  },
  {
    pattern: /\b(?:rendez[- ]vous|meetup|reuni[oó]n|encontro)\b/gi,
    map: { fr: 'rendez-vous', en: 'meet up', es: 'reunión', pt: 'encontro' }
  },
  {
    pattern: /\b(?:t[eé]l[eé]porte\s+au\s+donjon|teleport\s+to\s+(?:the\s+)?dungeon|teletransporta\s+a\s+la\s+mazmorra|teleporta\s+ao\s+calabou[çc]o)\b/gi,
    map: { fr: 'téléporte au donjon', en: 'teleport to dungeon', es: 'teletransporta a la mazmorra', pt: 'teleporta ao calabouço' }
  },
  {
    pattern: /\b(?:t[eé]l[eé]porte[- ]moi|teleport\s+me|teletransp[oó]rtame|teleporta-me)\b/gi,
    map: { fr: 'téléporte-moi', en: 'teleport me', es: 'teletranspórtame', pt: 'teleporta-me' }
  },
  {
    pattern: /\b(?:allons\s+au\s+zaap|let\'?s\s+go\s+to\s+(?:the\s+)?zaap|vamos\s+al\s+zaap|vamos\s+ao\s+zaap)\b/gi,
    map: { fr: 'allons au zaap', en: "let's go to the zaap", es: 'vamos al zaap', pt: 'vamos ao zaap' }
  },
  {
    pattern: /\b(?:sauvegarde\s+au\s+zaap|save\s+at\s+(?:the\s+)?zaap|guarda\s+en\s+el\s+zaap|salve\s+no\s+zaap)\b/gi,
    map: { fr: 'sauvegarde au zaap', en: 'save at the zaap', es: 'guarda en el zaap', pt: 'salve no zaap' }
  },
  {
    pattern: /\b(?:invite\s+dans\s+le\s+groupe|invite\s+to\s+(?:the\s+)?(?:party|group)|invita\s+al\s+grupo|convida\s+para\s+o\s+grupo)\b/gi,
    map: { fr: 'invite dans le groupe', en: 'invite to party', es: 'invita al grupo', pt: 'convida para o grupo' }
  },
  {
    pattern: /\b(?:gagner\s+de\s+l\'exp[eé]rience|gain\s+experience|farm\s+xp|levelear|upar)\b/gi,
    map: { fr: "gagner de l'expérience", en: 'farm XP', es: 'ganar experiencia', pt: 'ganhar experiência' }
  },
  {
    pattern: /\b(?:bien\s+jou[eé]\s+à\s+tous|good\s+game\s+everyone|bien\s+jugado\s+a\s+todos|bom\s+jogo\s+a\s+todos)\b/gi,
    map: { fr: 'bien joué à tous', en: 'good game everyone', es: 'bien jugado a todos', pt: 'bom jogo a todos' }
  },
  {
    pattern: /\b(?:[aà]\s+plus[,\s]+bon\s+jeu|see\s+you[,\s]+enjoy\s+the\s+game|hasta\s+luego[,\s]+buen\s+juego|at[eé]\s+mais[,\s]+bom\s+jogo)\b/gi,
    map: { fr: 'à plus, bon jeu', en: 'see you, enjoy the game', es: 'hasta luego, buen juego', pt: 'até mais, bom jogo' }
  },
  {
    pattern: /\b(?:bon\s+jeu|enjoy\s+the\s+game|buen\s+juego|bom\s+jogo)\b/gi,
    map: { fr: 'bon jeu', en: 'enjoy the game', es: 'buen juego', pt: 'bom jogo' }
  },
  {
    pattern: /\b(?:trousseau\s+de\s+clefs?|keyring|manojo\s+de\s+llaves|chaveiro)\b/gi,
    map: { fr: 'trousseau de clefs', en: 'keyring', es: 'manojo de llaves', pt: 'chaveiro' }
  },
  {
    pattern: /\b(?:donjon\s+Glours[eé]leste|celestial\s+bearbarian\s+dungeon|mazmorra\s+golosotr[oó]n\s+real|calabou[çc]o\s+glurseleste)\b/gi,
    map: { fr: 'donjon Glourséleste', en: 'Celestial Bearbarian Dungeon', es: 'mazmorra Golosotrón Real', pt: 'calabouço Glurseleste' }
  },
  {
    pattern: /\b(?:donjon\s+des\s+Bouftous|gobball\s+dungeon|mazmorra\s+de\s+los\s+jalat[oó]s|calabou[çc]o\s+dos\s+papatudos)\b/gi,
    map: { fr: 'donjon des Bouftous', en: 'Gobball Dungeon', es: 'mazmorra de los Jalatós', pt: 'calabouço dos Papatudos' }
  },
  {
    pattern: /\b(?:donjon\s+des\s+Blops|blop\s+dungeon|mazmorra\s+de\s+los\s+blops|calabou[çc]o\s+dos\s+blops)\b/gi,
    map: { fr: 'donjon des Blops', en: 'Blop Dungeon', es: 'mazmorra de los Blops', pt: 'calabouço dos Blops' }
  },
  {
    pattern: /\b(?:donjon\s+du\s+Meulou|moowolf\s+dungeon|mazmorra\s+del\s+maxilubo|calabou[çc]o\s+do\s+mulobo)\b/gi,
    map: { fr: 'donjon du Meulou', en: 'Moowolf Dungeon', es: 'mazmorra del Maxilubo', pt: 'calabouço do Mulobo' }
  },

  // Trade & Economy
  {
    pattern: /\b(?:offres\s+en\s+or|quick[- ]sell\s+offers|ofertas\s+en\s+oro|ofertas\s+em\s+ouro)\b/gi,
    map: { fr: 'offres en or', en: 'quick-sell offers', es: 'ofertas en oro', pt: 'ofertas em ouro' }
  },
  {
    pattern: /\b(?:pas\s+d\'arnaque|no\s+scams?|sin\s+estafas|sem\s+golpes)\b/gi,
    map: { fr: "pas d'arnaque", en: 'no scams', es: 'sin estafas', pt: 'sem golpes' }
  },
  {
    pattern: /\b(?:pas\s+de\s+d[eé]butant|no\s+noobs?|sin\s+novatos|sem\s+novatos)\b/gi,
    map: { fr: 'pas de débutant', en: 'no beginners', es: 'sin novatos', pt: 'sem novatos' }
  },
  {
    pattern: /\b(?:je\s+vends|selling|vendo)\b/gi,
    map: { fr: 'je vends', en: 'selling', es: 'vendo', pt: 'vendo' }
  },
  {
    pattern: /\b(?:j\'ach[eè]te|buying|compro)\b/gi,
    map: { fr: "j'achète", en: 'buying', es: 'compro', pt: 'compro' }
  },
  {
    pattern: /\bqui\s+veut\s+faire\s+(.+?)\s*\?/gi,
    map: (_match: string, p1: string) => ({
      fr: `qui veut faire ${p1} ?`,
      en: `who wants to do ${p1}?`,
      es: `¿quién quiere hacer ${p1}?`,
      pt: `quem quer fazer ${p1}?`
    })
  },
  {
    pattern: /\bon\s+va\s+faire\s+(.+)/gi,
    map: (_match: string, p1: string) => ({
      fr: `on va faire ${p1}`,
      en: `let's do ${p1}`,
      es: `vamos a hacer ${p1}`,
      pt: `vamos fazer ${p1}`
    })
  },
  {
    pattern: /\bon\s+va\s+combattre\s+(.+)/gi,
    map: (_match: string, p1: string) => ({
      fr: `on va combattre ${p1}`,
      en: `let's fight ${p1}`,
      es: `vamos a combatir ${p1}`,
      pt: `vamos combater ${p1}`
    })
  },

  // Dungeon keys
  {
    pattern: /\bcl[eé]\s+du\s+Bouftou\s+Royal\b/gi,
    map: { fr: 'clé du Bouftou Royal', en: 'Royal Gobball key', es: 'llave de Jalató Real', pt: 'chave de Papatudo Real' }
  },
  {
    pattern: /\bcl[eé]\s+du\s+Dragon\s+Cochon\b/gi,
    map: { fr: 'clé du Dragon Cochon', en: 'Dragon Pig key', es: 'llave de Dragocerdo', pt: 'chave de Dragão-Porco' }
  },
  {
    pattern: /\bcl[eé]\s+du\s+Chêne\s+Mou\b/gi,
    map: { fr: 'clé du Chêne Mou', en: 'Soft Oak key', es: 'llave de Roble Blando', pt: 'chave de Carvalho Mole' }
  },
  {
    pattern: /\bcl[eé]\s+du\s+Royalmouth\b/gi,
    map: { fr: 'clé du Royalmouth', en: 'Royal Mastogob key', es: 'llave de Jalamut Real', pt: 'chave de Papatudo da Neve Real' }
  }
];
