import { DofusEntry, DofusLanguage } from '../../types/dofus';
import {
  DOFUS_DIMENSIONS_AND_ZONES,
  DOFUS_CLASSES_FR_EN,
  DOFUS_CLASSES_ALL_LANGS,
  DOFUS_ARCHIMONSTERS_AND_WANTED,
  DOFUS_CHAT_IDIOMS_FR_TO_EN,
  DOFUS_CHAT_IDIOMS_EN_TO_FR
} from '../../data/dofusExpandedData';
import { DOFUS_QUESTS_AND_BOUNTIES_ENTRIES } from '../../data/dofusQuestsAndBounties';
import { GENERIC_CONVERSATIONAL_WORDS, escapeRegExp } from './constants';
import { normalizeFrenchGamingChat, normalizeEnglishGamingChat, normalizeIberianGamingChat } from './normalizers';
import { MULTI_LANG_TOKEN_RULES } from './tokenRules';
import { polishEnglishArticles } from './gtxEngine';
import { guessChatLanguage } from './languageDetect';

/**
 * Question patterns & complex verb structures frequently used in MMORPG Dofus chat
 */
const FR_QUESTION_AND_VERB_PATTERNS: [RegExp, string][] = [
  [/^combattre\s+(.+?)[,\s]+ça\s+te\s+dit\s*\?$/i, 'down for fighting $1?'],
  [/^faire\s+(.+?)[,\s]+ça\s+te\s+dit\s*\?$/i, 'down for doing $1?'],
  [/^(.+?)[,\s]+ça\s+te\s+dit\s*\?$/i, 'are you down for $1?'],
  [/^ça\s+te\s+dit\s*\?$/i, 'are you down?'],
  [/^ça\s+vous\s+dit\s*\?$/i, 'are you guys down?'],
  [/^qui\s+veut\s+faire\s+un\s+(.+)\s*\?$/i, 'who wants to do a $1?'],
  [/^qui\s+veut\s+faire\s+(.+)\s*\?$/i, 'who wants to do $1?'],
  [/^qui\s+veut\s+combattre\s+(.+)\s*\?$/i, 'who wants to fight $1?'],
  [/^on\s+va\s+combattre\s+(.+)$/i, "let's fight $1"],
  [/^on\s+va\s+faire\s+(.+)$/i, "let's do $1"],
  [/^on\s+fait\s+un\s+(.+)\s*\?$/i, 'shall we do a $1?'],
  [/^on\s+fait\s+une\s+(.+)\s*\?$/i, 'shall we do a $1?'],
  [/^on\s+fait\s+les\s+(.+)\s*\?$/i, 'shall we do the $1?'],
  [/^on\s+fait\s+des\s+(.+)\s*\?$/i, 'shall we do some $1?'],
  [/^on\s+fait\s+(.+)\s*\?$/i, 'shall we do $1?'],
  [/^on\s+tente\s+un\s+(.+)\s*\?$/i, 'shall we try a $1?'],
  [/^on\s+tente\s+le\s+(.+)\s*\?$/i, 'shall we try the $1?'],
  [/^on\s+tente\s+les\s+(.+)\s*\?$/i, 'shall we try the $1?'],
  [/^on\s+tente\s+(.+)\s*\?$/i, 'shall we try $1?'],
  [/^on\s+lance\s*\?$/i, 'shall we start?'],
  [/^on\s+lance\s+(.+)\s*\?$/i, 'shall we start $1?'],
  [/^on\s+y\s+va\s*\?$/i, 'shall we go?'],
  [/^tu\s+viens\s*\?$/i, 'are you coming?'],
  [/^tu\s+viens\s+pour\s+(.+)\s*\?$/i, 'are you coming for $1?'],
  [/^tu\s+fais\s+quoi\s*\?$/i, 'what are you doing?'],
  [/^tu\s+fais\s+(.+)\s*\?$/i, 'are you doing $1?'],
  [/^qui\s+est\s+chaud\s*\?$/i, 'who is up?'],
  [/^qui\s+est\s+chaud\s+pour\s+(.+)\s*\?$/i, 'who is up for $1?'],
  [/^qui\s+veut\s+venir\s*\?$/i, 'who wants to come?'],
  [/^qui\s+veut\s+(.+)\s*\?$/i, 'who wants $1?'],
  [/^qui\s+peut\s+m'aider\s*\?$/i, 'who can help me?'],
  [/^qui\s+peut\s+aider\s*\?$/i, 'who can help?'],
  [/^qui\s+gère\s+(.+)\s*\?$/i, 'who can carry $1?'],
  [/^qui\s+a\s+(.+)\s*\?$/i, 'who has $1?'],
  [/^quelqu'un\s+a\s+(.+)\s*\?$/i, 'does anyone have $1?'],
  [/^combien\s+ça\s+vaut\s*\?$/i, 'how much is it worth?'],
  [/^combien\s+ça\s+coûte\s*\?$/i, 'how much does it cost?'],
  [/\bon\s+fait\s+un\b/gi, 'we are doing a'],
  [/\bon\s+fait\s+une\b/gi, 'we are doing a'],
  [/\bon\s+fait\s+les\b/gi, 'we are doing the'],
  [/\bon\s+fait\s+des\b/gi, 'we are doing'],
  [/\bon\s+fait\b/gi, 'we do'],
  [/\bon\s+tente\b/gi, 'we are trying'],
  [/\bon\s+lance\b/gi, 'we are starting'],
  [/\btu\s+fais\s+un\b/gi, 'you are doing a'],
  [/\btu\s+fais\s+une\b/gi, 'you are doing a'],
  [/\btu\s+fais\b/gi, 'you are doing'],
  [/\bje\s+fais\s+un\b/gi, 'I am doing a'],
  [/\bje\s+fais\s+une\b/gi, 'I am doing a'],
  [/\bje\s+fais\b/gi, 'I am doing'],
  [/\bqui\s+fait\b/gi, 'who is doing'],
  [/\bqui\s+a\b/gi, 'who has'],
  [/\bfait\s+un\b/gi, 'do a'],
  [/\bfait\s+une\b/gi, 'do a'],
  [/\bfais\s+un\b/gi, 'do a'],
  [/\bfais\s+une\b/gi, 'do a'],
  [/\bfaire\s+un\b/gi, 'do a'],
  [/\bfaire\s+une\b/gi, 'do a'],
  [/\bfaire\s+les\b/gi, 'do the'],
  [/\bfaire\b/gi, 'do'],
  [/\bfait\b/gi, 'done'],
  [/\bfais\b/gi, 'do'],
  [/\bfont\b/gi, 'do'],
  [/\bj'arrive\b/gi, "I'm coming"],
  [/\bje\s+viens\b/gi, "I'm coming"],
  [/\btu\s+peux\s+m'aider\b/gi, 'can you help me'],
  [/\btu\s+peux\s+aider\b/gi, 'can you help'],
  [/\bje\s+peux\s+aider\b/gi, 'I can help'],
  [/\bon\s+peut\s+m'aider\b/gi, 'can someone help me'],
  [/\bon\s+peut\s+aider\b/gi, 'can someone help'],
  [/\bcherche\s+aide\b/gi, 'looking for help'],
  [/\bbesoin\s+d'aide\b/gi, 'need help'],
  [/\bbesoin\s+aide\b/gi, 'need help'],
  [/\bdemande\s+d'aide\b/gi, 'asking for help'],
  [/\bje\s+cherche\s+un\b/gi, 'I am looking for a'],
  [/\bje\s+cherche\s+une\b/gi, 'I am looking for a'],
  [/\bje\s+cherche\s+des\b/gi, 'I am looking for'],
  [/\bje\s+cherche\b/gi, 'I am looking for'],
  [/\bon\s+cherche\s+un\b/gi, 'we are looking for a'],
  [/\bon\s+cherche\s+une\b/gi, 'we are looking for a'],
  [/\bon\s+cherche\s+des\b/gi, 'we are looking for'],
  [/\bon\s+cherche\b/gi, 'we are looking for'],
  [/\bcherche\s+un\b/gi, 'looking for a'],
  [/\bcherche\s+une\b/gi, 'looking for a'],
  [/\bcherche\s+des\b/gi, 'looking for'],
  [/\brecrute\s+un\b/gi, 'recruiting a'],
  [/\brecrute\s+une\b/gi, 'recruiting a'],
  [/\brecrute\s+des\b/gi, 'recruiting'],
  [/\bje\s+recrute\b/gi, 'I am recruiting'],
  [/\bon\s+recrute\b/gi, 'we are recruiting'],
  [/\bje\s+vends\s+un\b/gi, 'I am selling a'],
  [/\bje\s+vends\s+une\b/gi, 'I am selling a'],
  [/\bje\s+vends\s+des\b/gi, 'I am selling'],
  [/\bje\s+vends\b/gi, 'I am selling'],
  [/\bon\s+vends\b/gi, 'we are selling'],
  [/\bvends\s+un\b/gi, 'selling a'],
  [/\bvends\s+une\b/gi, 'selling a'],
  [/\bvends\s+des\b/gi, 'selling'],
  [/\bje\s+veux\s+vendre\b/gi, 'I want to sell'],
  [/\bje\s+veux\s+acheter\b/gi, 'I want to buy'],
  [/\bje\s+veux\b/gi, 'I want'],
  [/\bon\s+veut\b/gi, 'we want'],
  [/\btu\s+veux\b/gi, 'you want'],
  [/\bj'achète\s+un\b/gi, 'I am buying a'],
  [/\bj'achète\s+une\b/gi, 'I am buying a'],
  [/\bj'achète\s+des\b/gi, 'I am buying'],
  [/\bj'achète\b/gi, 'I am buying'],
  [/\bachète\s+un\b/gi, 'buying a'],
  [/\bachète\s+une\b/gi, 'buying a'],
  [/\bachète\s+des\b/gi, 'buying'],
  [/\bachète\b/gi, 'buying'],
  [/\bj'ai\s+trouvé\b/gi, 'I found'],
  [/\btu\s+as\s+trouvé\b/gi, 'you found'],
  [/\bt'as\s+trouvé\b/gi, 'you found'],
  [/\btrouvé\b/gi, 'found'],
  [/\btrouve\b/gi, 'find'],
  [/\bcherche\b/gi, 'looking for'],
  [/\bcherchons\b/gi, 'looking for'],
  [/\bvends\b/gi, 'selling'],
  [/\bvend\b/gi, 'selling'],
  [/\brecrute\b/gi, 'recruiting'],
  [/\brecrutons\b/gi, 'recruiting'],
  [/\bpartant\b/gi, 'down for it'],
  [/\bpartante\b/gi, 'down for it'],
  [/\bchaud\b/gi, 'down'],
  [/\bchaude\b/gi, 'down']
];

const FR_EN_COMMON_GRAMMAR: [RegExp, string][] = [
  [/\bbonjour\b/gi, 'hello'],
  [/\bsalut\b/gi, 'hi'],
  [/\bmerci\b/gi, 'thank you'],
  [/\bde rien\b/gi, "you're welcome"],
  [/\bs'il vous plaît\b/gi, 'please'],
  [/\bs'il te plaît\b/gi, 'please'],
  [/\bà plus\b/gi, 'cya'],
  [/\bcombien\b/gi, 'how much'],
  [/\bpourquoi\b/gi, 'why'],
  [/\btous\b/gi, 'all'],
  [/\btout\b/gi, 'all'],
  [/\brien\b/gi, 'nothing'],
  [/\bmon\b/gi, 'my'],
  [/\bma\b/gi, 'my'],
  [/\bmes\b/gi, 'my'],
  [/\bton\b/gi, 'your'],
  [/\bta\b/gi, 'your'],
  [/\btes\b/gi, 'your'],
  [/\bson\b/gi, 'his'],
  [/\bsa\b/gi, 'her'],
  [/\bses\b/gi, 'his'],
  [/\bnotre\b/gi, 'our'],
  [/\bnos\b/gi, 'our'],
  [/\bvotre\b/gi, 'your'],
  [/\bvos\b/gi, 'your'],
  [/\bleur\b/gi, 'their'],
  [/\bleurs\b/gi, 'their'],
  [/\bun\b/gi, 'a'],
  [/\bune\b/gi, 'a'],
  [/\ble\b/gi, 'the'],
  [/\bla\b/gi, 'the'],
  [/\bles\b/gi, 'the'],
  [/\bdes\b/gi, '']
];

const PT_FR_COMMON_GRAMMAR: [RegExp, string][] = [
  [/\brecruto\b/gi, 'recrute'],
  [/\bprocuro\b/gi, 'cherche'],
  [/\bcompro\b/gi, 'achète'],
  [/\bvendo\b/gi, 'vends'],
  [/\bqualquer\s+(?:lv+l|n[ií]vel|nv)\b/gi, 'tout niveau'],
  [/\bqualquer\b/gi, 'tout'],
  [/\b(?:lv+l|n[ií]vel|nv)\b/gi, 'niveau'],
  [/\bfocado\s+em\b/gi, 'orienté'],
  [/\bfocado\b/gi, 'orienté'],
  [/\bcoletores\b/gi, 'percepteurs'],
  [/\bcoletor\b/gi, 'percepteur'],
  [/\bcalabou[cç]os?\b/gi, 'donjon'],
  [/\bvagas?\b/gi, 'places'],
  [/\bchaveiro\b/gi, 'trousseau de clefs'],
  [/\bcada\s+um\b/gi, 'par unité'],
  [/\bcad[êe]\b/gi, 'où est'],
  [/\bestamos\s+juntos\b/gi, 'gg ensemble'],
  [/\bcombinado\b/gi, 'ça marche'],
  [/\bat[ée]\s+mais\b/gi, 'à plus'],
  [/\btudo\s+bem\b/gi, 'ça va'],
  [/\bdispon[ií]vel\b/gi, 'disponible'],
  [/\bpor\s+favor\b/gi, "s'il vous plaît"],
  [/\bobrigad[oa]\b/gi, 'merci'],
  [/\bpara\b/gi, 'pour'],
  [/\bcom\b/gi, 'avec'],
  [/\bsem\b/gi, 'sans'],
  [/\bem\b/gi, 'en'],
  [/\be\b/gi, 'et'],
  [/\bou\b/gi, 'ou']
];

const ES_FR_COMMON_GRAMMAR: [RegExp, string][] = [
  [/\bhola\b/gi, 'salut'],
  [/\brecluto\b/gi, 'recrute'],
  [/\bbusco\b/gi, 'cherche'],
  [/\bcompro\b/gi, 'achète'],
  [/\bvendo\b/gi, 'vends'],
  [/\bcualquier\s+(?:lv+l|nivel|nv)\b/gi, 'tout niveau'],
  [/\bcualquier\b/gi, 'tout'],
  [/\b(?:lv+l|nivel|nv)\b/gi, 'niveau'],
  [/\benfocado\s+en\b/gi, 'orienté'],
  [/\brecaudadores\b/gi, 'percepteurs'],
  [/\brecaudador\b/gi, 'percepteur'],
  [/\bmazmorras?\b/gi, 'donjon'],
  [/\bplazas?\b/gi, 'places'],
  [/\bmanojo\s+de\s+llaves\b/gi, 'trousseau de clefs'],
  [/\bllaves?\b/gi, 'clé'],
  [/\bcada\s+uno\b/gi, 'par unité'],
  [/\bd[óo]nde\b/gi, 'où'],
  [/\bno\s+te\s+preocupes\b/gi, "t'inquiète"],
  [/\btambi[ée]n\b/gi, 'aussi'],
  [/\bdisponible\b/gi, 'disponible'],
  [/\bpor\s+favor\b/gi, "s'il vous plaît"],
  [/\bgracias\b/gi, 'merci'],
  [/\bpara\b/gi, 'pour'],
  [/\bcon\b/gi, 'avec'],
  [/\bsin\b/gi, 'sans'],
  [/\by\b/gi, 'et'],
  [/\bo\b/gi, 'ou']
];

const FR_ES_COMMON_GRAMMAR: [RegExp, string][] = [
  [/\bhello\b|\bsalut\b|\bbonjour\b/gi, 'hola'],
  [/\brecrute\b/gi, 'recluto'],
  [/\bcherche\b/gi, 'busco'],
  [/\bach[eè]te\b/gi, 'compro'],
  [/\bvends?\b/gi, 'vendo'],
  [/\bbricoleur\b/gi, 'manitas'],
  [/\bniveau\b/gi, 'nivel'],
  [/\bde\s+disponible\b/gi, 'disponible'],
  [/\bdispo(?:nible)?\b/gi, 'disponible'],
  [/\bs'il\s+(?:vous|te)\s+pla[iî]t\b|\bsvp\b|\bstp\b/gi, 'por favor'],
  [/\bpano(?:plie)?\s+sasa\b/gi, 'set de sabiduría'],
  [/\bcontre\s+caution\b/gi, 'con fianza'],
  [/\btr[eè]s\s+rapide\b/gi, 'muy rápido'],
  [/\bmeilleur\b/gi, 'mejor'],
  [/\bpar\s+combat\b/gi, 'por combate'],
  [/\bpour\b/gi, 'para'],
  [/\bavec\b/gi, 'con'],
  [/\bsans\b/gi, 'sin'],
  [/\bet\b/gi, 'y']
];

const FR_PT_COMMON_GRAMMAR: [RegExp, string][] = [
  [/\bhello\b|\bsalut\b|\bbonjour\b/gi, 'olá'],
  [/\brecrute\b/gi, 'recruto'],
  [/\bcherche\b/gi, 'procuro'],
  [/\bach[eè]te\b/gi, 'compro'],
  [/\bvends?\b/gi, 'vendo'],
  [/\bbricoleur\b/gi, 'faz-tudo'],
  [/\bniveau\b/gi, 'nível'],
  [/\bde\s+disponible\b/gi, 'disponível'],
  [/\bdispo(?:nible)?\b/gi, 'disponível'],
  [/\bs'il\s+(?:vous|te)\s+pla[iî]t\b|\bsvp\b|\bstp\b/gi, 'por favor'],
  [/\bpano(?:plie)?\s+sasa\b/gi, 'conjunto de sabedoria'],
  [/\bcontre\s+caution\b/gi, 'com caução'],
  [/\btr[eè]s\s+rapide\b/gi, 'muito rápido'],
  [/\bmeilleur\b/gi, 'melhor'],
  [/\bpar\s+combat\b/gi, 'por combate'],
  [/\bpour\b/gi, 'para'],
  [/\bavec\b/gi, 'com'],
  [/\bsans\b/gi, 'sem'],
  [/\bet\b/gi, 'e'],
  [/\bun\b/gi, 'um'],
  [/\bune\b/gi, 'uma']
];

const ES_EN_COMMON_GRAMMAR: [RegExp, string][] = [
  [/\bhola\b/gi, 'hello'],
  [/\brecluto\b/gi, 'recruiting'],
  [/\bbusco\b/gi, 'looking for'],
  [/\bcompro\b/gi, 'buying'],
  [/\bvendo\b/gi, 'selling'],
  [/\b(?:quién|quien)\b/gi, 'who'],
  [/\balguien\b/gi, 'anyone'],
  [/\bmazmorras?\b/gi, 'dungeon'],
  [/\bplazas?\b/gi, 'spots'],
  [/\bllaves?\b/gi, 'key'],
  [/\brecaudadores\b/gi, 'perceptors'],
  [/\brecaudador\b/gi, 'perceptor'],
  [/\bmonstruos\b/gi, 'monsters'],
  [/\bmonstruo\b/gi, 'monster'],
  [/\bcada\s+uno\b/gi, 'each'],
  [/\bd[óo]nde\b/gi, 'where'],
  [/\bno\s+te\s+preocupes\b/gi, 'no worries'],
  [/\btambi[ée]n\b/gi, 'also'],
  [/\bpor\s+favor\b/gi, 'please'],
  [/\bgracias\b/gi, 'thank you'],
  [/\bnivel\b/gi, 'level'],
  [/\bdisponible\b/gi, 'available'],
  [/\bpara\b/gi, 'for'],
  [/\bcon\b/gi, 'with'],
  [/\bsin\b/gi, 'without'],
  [/\by\b/gi, 'and']
];

const PT_EN_COMMON_GRAMMAR: [RegExp, string][] = [
  [/\bol[áa]\b/gi, 'hello'],
  [/\brecruto\b/gi, 'recruiting'],
  [/\bprocuro\b/gi, 'looking for'],
  [/\bcompro\b/gi, 'buying'],
  [/\bvendo\b/gi, 'selling'],
  [/\bquem\b/gi, 'who'],
  [/\balgu[ée]m\b/gi, 'anyone'],
  [/\bcalabou[cç]os?\b/gi, 'dungeon'],
  [/\bvagas?\b/gi, 'spots'],
  [/\bchaves?\b/gi, 'key'],
  [/\bcoletores\b/gi, 'perceptors'],
  [/\bcoletor\b/gi, 'perceptor'],
  [/\bmonstros\b/gi, 'monsters'],
  [/\bmonstro\b/gi, 'monster'],
  [/\bcada\s+um\b/gi, 'each'],
  [/\bcad[êe]\b/gi, 'where is'],
  [/\bestamos\s+juntos\b/gi, 'cheers'],
  [/\bcombinado\b/gi, 'sounds good'],
  [/\btudo\s+bem\b/gi, 'all good'],
  [/\bpor\s+favor\b/gi, 'please'],
  [/\bobrigad[oa]\b/gi, 'thank you'],
  [/\bn[ií]vel\b/gi, 'level'],
  [/\bdispon[ií]vel\b/gi, 'available'],
  [/\bpara\b/gi, 'for'],
  [/\bcom\b/gi, 'with'],
  [/\bsem\b/gi, 'without'],
  [/\be\b/gi, 'and']
];

const EN_ES_COMMON_GRAMMAR: [RegExp, string][] = [
  [/\bhello\b|\bhi\b/gi, 'hola'],
  [/\blooking\s+for\b/gi, 'busco'],
  [/\brecruiting\b/gi, 'recluto'],
  [/\bselling\b/gi, 'vendo'],
  [/\bbuying\b/gi, 'compro'],
  [/\bdungeon\b/gi, 'mazmorra'],
  [/\bspots\b/gi, 'plazas'],
  [/\bspot\b/gi, 'plaza'],
  [/\bplease\b/gi, 'por favor'],
  [/\bthank\s+you\b/gi, 'gracias'],
  [/\blevel\b/gi, 'nivel'],
  [/\bfor\b/gi, 'para'],
  [/\bwith\b/gi, 'con'],
  [/\bwithout\b/gi, 'sin'],
  [/\band\b/gi, 'y']
];

const EN_PT_COMMON_GRAMMAR: [RegExp, string][] = [
  [/\bhello\b|\bhi\b/gi, 'olá'],
  [/\blooking\s+for\b/gi, 'procuro'],
  [/\brecruiting\b/gi, 'recruto'],
  [/\bselling\b/gi, 'vendo'],
  [/\bbuying\b/gi, 'compro'],
  [/\bdungeon\b/gi, 'calabouço'],
  [/\bspots\b/gi, 'vagas'],
  [/\bspot\b/gi, 'vaga'],
  [/\bplease\b/gi, 'por favor'],
  [/\bthank\s+you\b/gi, 'obrigado'],
  [/\blevel\b/gi, 'nível'],
  [/\bfor\b/gi, 'para'],
  [/\bwith\b/gi, 'com'],
  [/\bwithout\b/gi, 'sem'],
  [/\band\b/gi, 'e']
];

const EN_FR_COMMON_GRAMMAR: [RegExp, string][] = [
  [/^shall we do an? (.+)\?$/i, 'on fait un $1 ?'],
  [/^shall we do the (.+)\?$/i, 'on fait le $1 ?'],
  [/^shall we do (.+)\?$/i, 'on fait $1 ?'],
  [/^shall we try (.+)\?$/i, 'on tente $1 ?'],
  [/^shall we start\?$/i, 'on lance ?'],
  [/^shall we go\?$/i, 'on y va ?'],
  [/^are you coming\?$/i, 'tu viens ?'],
  [/^what are you doing\?$/i, 'tu fais quoi ?'],
  [/^who is up\?$/i, 'qui est chaud ?'],
  [/^who wants to (.+)\?$/i, 'qui veut $1 ?'],
  [/^who can help\?$/i, 'qui peut aider ?'],
  [/^who can carry (.+)\?$/i, 'qui gère $1 ?'],
  [/^does anyone have (.+)\?$/i, "quelqu'un a $1 ?"],
  [/\bavailable\b/gi, 'disponible'],
  [/\bplease\b/gi, "s'il vous plaît"],
  [/\bhandyman\b/gi, 'bricoleur'],
  [/\blevel\b/gi, 'niveau'],
  [/\bif\b/gi, 'si'],
  [/\byou see\b/gi, 'vous voyez'],
  [/\byou find\b/gi, 'vous trouvez'],
  [/\bi am\b/gi, 'je suis'],
  [/\bi'm\b/gi, 'je suis'],
  [/\bwe are\b/gi, 'nous sommes'],
  [/\bwe're\b/gi, 'on est'],
  [/\byou are\b/gi, 'vous êtes'],
  [/\byou're\b/gi, 'vous êtes'],
  [/\blooking for\b/gi, 'cherche'],
  [/\binterested\b/gi, 'preneur'],
  [/\bin\b/gi, 'en'],
  [/\bor\b/gi, 'ou'],
  [/\band\b/gi, 'et'],
  [/\bwith\b/gi, 'avec'],
  [/\bwithout\b/gi, 'sans'],
  [/\bfor\b/gi, 'pour'],
  [/\bhere\b/gi, 'ici'],
  [/\bthere\b/gi, 'là'],
  [/\bnow\b/gi, 'maintenant'],
  [/\bwho\b/gi, 'qui'],
  [/\bwhat\b/gi, 'quoi'],
  [/\bwhere\b/gi, 'où'],
  [/\bthe\s+([A-ZÀ-ÿ][a-zà-ÿ]+s)\b/g, 'les $1'],
  [/\bthe\s+([A-ZÀ-ÿ][a-zà-ÿ]+)\b/g, 'le $1'],
  [/\bgroup\b/gi, 'groupe'],
  [/\bparty\b/gi, 'groupe']
];

function applySharedTokenRules(text: string, targetLang: DofusLanguage): string {
  let output = text;
  for (const rule of MULTI_LANG_TOKEN_RULES) {
    rule.pattern.lastIndex = 0;
    if (rule.pattern.test(output)) {
      rule.pattern.lastIndex = 0;
      output = output.replace(rule.pattern, (match, ...args) => {
        let resolvedTarget: any = typeof rule.map === 'function' ? rule.map(match, ...args) : rule.map;
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
        return String(resolvedTarget);
      });
      rule.pattern.lastIndex = 0;
    }
  }
  return output;
}

/**
 * Main Universal Offline Translator Function (100% offline fallback across FR, EN, ES, PT)
 */
export function translateUniversally(
  text: string,
  entries: DofusEntry[],
  sourceLangInput: DofusLanguage | 'auto',
  targetLang: DofusLanguage
): string {
  if (!text || !text.trim()) return text;
  const sourceLang: DofusLanguage = sourceLangInput === 'auto' ? guessChatLanguage(text) : sourceLangInput;
  if (sourceLang === targetLang) return text;

  let chatCommandPrefix = '';
  let workingText = text.trim();
  const cmdMatch = workingText.match(/^(\/(?:w\s+(?:\*[^*]+\*|\S+)|p|g|k|a|b|s|m)\s+)/i);
  if (cmdMatch) {
    chatCommandPrefix = cmdMatch[1];
    workingText = workingText.slice(chatCommandPrefix.length).trim();
  }

  let output = workingText;

  const cachedOnWindow = typeof window !== 'undefined' ? (window as any).__dofus_cached_entries : null;
  const combinedEntries = entries && entries.length > 500
    ? entries
    : (cachedOnWindow && cachedOnWindow.length > 500
      ? cachedOnWindow
      : [...DOFUS_QUESTS_AND_BOUNTIES_ENTRIES, ...(entries || [])]);

  // Fast exact match check for single Quest / Monster / Dungeon / Dofus / Spell / Achievement title
  const isBracketedOnly = /^\[[^\]]+\]$/.test(output);
  const lowerTrimmed = (isBracketedOnly ? output.slice(1, -1).trim() : output).toLowerCase();

  for (const item of combinedEntries) {
    const targetVal = item[targetLang] || item.en || item.fr;
    if (!targetVal) continue;
    const isMatch = sourceLang === 'fr'
      ? (item.fr.toLowerCase() === lowerTrimmed || item.aliases_fr?.some((a: string) => a.toLowerCase() === lowerTrimmed))
      : (item[sourceLang]?.toLowerCase() === lowerTrimmed);
    if (isMatch) {
      return isBracketedOnly ? `[${targetVal}]` : targetVal;
    }
  }

  if (sourceLang === 'fr') {
    output = normalizeFrenchGamingChat(output);
  } else if (sourceLang === 'en') {
    output = normalizeEnglishGamingChat(output);
  } else if (sourceLang === 'pt' || sourceLang === 'es') {
    output = normalizeIberianGamingChat(output, sourceLang);
  }

  // Offline rule replacements involving ES or PT
  if ((sourceLang !== 'fr' && sourceLang !== 'en') || (targetLang !== 'fr' && targetLang !== 'en')) {
    // 1. Apply 4-language shared token rules first
    output = applySharedTokenRules(output, targetLang);

    // 2. Apply 4-language classes
    for (const c of DOFUS_CLASSES_ALL_LANGS) {
      const terms = [c.fr, c.en, c.es, c.pt, ...c.short];
      for (const term of terms) {
        if (!term || term.length < 3) continue;
        const clsRegex = new RegExp(`(?:^|\\b)${escapeRegExp(term)}(?=\\s|$|[-.,?!/])`, 'gi');
        output = output.replace(clsRegex, c[targetLang]);
      }
    }

    // 3. Dictionary entries with placeholder protection
    const lowerOut = output.toLowerCase();
    const matchedPairs: { cand: string; target: string }[] = [];
    for (const item of combinedEntries) {
      const targetVal = item[targetLang];
      if (!targetVal) continue;
      const srcPrimary = item[sourceLang] || '';
      if (item.context_sensitive && !srcPrimary.includes(' ')) continue;
      const candidates = sourceLang === 'fr'
        ? [item.fr, ...(item.aliases_fr || [])]
        : [srcPrimary];
      for (const cand of candidates) {
        if (!cand || cand.length < 3) continue;
        const candLow = cand.toLowerCase().trim();
        if (GENERIC_CONVERSATIONAL_WORDS.has(candLow)) continue;
        if (lowerOut.includes(candLow)) {
          matchedPairs.push({ cand, target: targetVal });
        }
      }
    }
    const placeholders: { ph: string; target: string }[] = [];
    matchedPairs.sort((a, b) => b.cand.length - a.cand.length);
    for (const pair of matchedPairs) {
      const regex = new RegExp(`(?:^|\\b)${escapeRegExp(pair.cand)}(?=\\s|$|[.,?!\\]])`, 'gi');
      if (regex.test(output)) {
        regex.lastIndex = 0;
        const ph = `__OFFTOK_${placeholders.length}__`;
        placeholders.push({ ph, target: pair.target });
        output = output.replace(regex, ph);
      }
    }

    const grammarRules =
      sourceLang === 'pt' && targetLang === 'fr' ? PT_FR_COMMON_GRAMMAR :
      sourceLang === 'es' && targetLang === 'fr' ? ES_FR_COMMON_GRAMMAR :
      sourceLang === 'fr' && targetLang === 'es' ? FR_ES_COMMON_GRAMMAR :
      sourceLang === 'fr' && targetLang === 'pt' ? FR_PT_COMMON_GRAMMAR :
      sourceLang === 'es' && targetLang === 'en' ? ES_EN_COMMON_GRAMMAR :
      sourceLang === 'pt' && targetLang === 'en' ? PT_EN_COMMON_GRAMMAR :
      sourceLang === 'en' && targetLang === 'es' ? EN_ES_COMMON_GRAMMAR :
      sourceLang === 'en' && targetLang === 'pt' ? EN_PT_COMMON_GRAMMAR :
      sourceLang === 'es' && targetLang === 'pt' ? [...ES_EN_COMMON_GRAMMAR, ...EN_PT_COMMON_GRAMMAR] :
      sourceLang === 'pt' && targetLang === 'es' ? [...PT_EN_COMMON_GRAMMAR, ...EN_ES_COMMON_GRAMMAR] : [];

    for (const [pattern, repl] of grammarRules) {
      output = output.replace(pattern, repl);
    }

    for (let i = placeholders.length - 1; i >= 0; i--) {
      output = output.split(placeholders[i].ph).join(placeholders[i].target);
    }

    const finalRes = output.replace(/\s+,/g, ',').replace(/\s{2,}/g, ' ').trim();
    return chatCommandPrefix ? chatCommandPrefix + finalRes : finalRes;
  }

  if (sourceLang === 'fr' && targetLang === 'en') {
    let matchedQuestion = false;
    for (const [pattern, repl] of FR_QUESTION_AND_VERB_PATTERNS) {
      if (pattern.test(output)) {
        output = output.replace(pattern, repl);
        matchedQuestion = true;
        break;
      }
    }

    for (const [pattern, repl] of DOFUS_CHAT_IDIOMS_FR_TO_EN) {
      output = output.replace(pattern, repl);
    }

    output = applySharedTokenRules(output, targetLang);

    for (const [frZone, enZone] of Object.entries(DOFUS_DIMENSIONS_AND_ZONES)) {
      if (!output.toLowerCase().includes(frZone.toLowerCase())) continue;
      const regex = new RegExp(`(?:^|\\b)${escapeRegExp(frZone)}(?=\\s|$|[.,?!])`, 'gi');
      output = output.replace(regex, enZone);
    }

    for (const [frMob, enMob] of Object.entries(DOFUS_ARCHIMONSTERS_AND_WANTED)) {
      if (!output.toLowerCase().includes(frMob.toLowerCase())) continue;
      const regex = new RegExp(`(?:^|\\b)${escapeRegExp(frMob)}(?=\\s|$|[.,?!])`, 'gi');
      output = output.replace(regex, enMob);
    }

    for (const [frClass, info] of Object.entries(DOFUS_CLASSES_FR_EN)) {
      const classTerms = [frClass, ...info.short];
      for (const term of classTerms) {
        if (!output.toLowerCase().includes(term.toLowerCase())) continue;
        const regex = new RegExp(`\\b${escapeRegExp(term)}\\b`, 'gi');
        output = output.replace(regex, info.en);
      }
    }

    output = output.replace(/\bpano(?:plie)?\s+sasa\b/gi, 'wisdom set');
    output = output.replace(/\bpano(?:plie)?\s+pp\b/gi, 'prospecting set');
    output = output.replace(/\bbricoleur\b/gi, 'handyman');
    output = output.replace(/\bmule\s+(?:a|à)?\s*sagesse\b/gi, 'wisdom alt');
    output = output.replace(/\bmule\s+(?:a|à)?\s*sasa\b/gi, 'wisdom alt');
    output = output.replace(/\bmule\b/gi, 'alt');
    output = output.replace(/\bpersonnage\b/gi, 'character');
    output = output.replace(/\bprix\s+fixe\b/gi, 'firm price');
    output = output.replace(/\bprix\s+ferme\b/gi, 'firm price');
    output = output.replace(/\bachat\s+revente\b/gi, 'buying & reselling');
    output = output.replace(/\bsauvegarde\s+boss\b/gi, 'saved at boss');
    output = output.replace(/\bpassage\s+donjon\b/gi, 'dungeon carry');
    output = output.replace(/\bpasseur\b/gi, 'carry');
    output = output.replace(/\b(\d+)\s+places?\b/gi, '$1 spots');
    output = output.replace(/\b(\d+)\s+glaces?\b/gi, '$1 spots');
    output = output.replace(/\b(?:une?|1)\s+place\b/gi, '1 spot');
    output = output.replace(/\b(?:une?|1)\s+glace\b/gi, '1 spot');
    output = output.replace(/\b(?:tacle\s+et\s+fuite|fuite\s+et\s+tacle)\b/gi, 'lock and dodge');
    output = output.replace(/\bdu\s+tacle\b/gi, 'lock');
    output = output.replace(/\bde\s+la\s+fuite\b/gi, 'dodge');
    output = output.replace(/\btacle\b/gi, 'lock');
    output = output.replace(/\bfuite\b/gi, 'dodge');
    output = output.replace(/\bdalles?\b/gi, 'pressure plates');
    output = output.replace(/\bpuits\s*pa\b/gi, 'AP sink');
    output = output.replace(/\bpuits\s*pm\b/gi, 'MP sink');

    // Dofus monster families & mob expressions (offline fr -> en)
    output = output.replace(/\bles\s+mobs\s+ravageurs\b/gi, 'the Destroyer mobs');
    output = output.replace(/\bmobs\s+ravageurs\b/gi, 'Destroyer mobs');
    output = output.replace(/\ble\s+mob\s+ravageur\b/gi, 'the Destroyer mob');
    output = output.replace(/\bun\s+mob\s+ravageur\b/gi, 'a Destroyer mob');
    output = output.replace(/\bmob\s+ravageur\b/gi, 'Destroyer mob');
    output = output.replace(/\bfamille\s+des\s+ravageurs\b/gi, 'Destroyers family');
    output = output.replace(/\bles\s+ravageurs\b/gi, 'the Destroyers');
    output = output.replace(/\ble\s+ravageur\b/gi, 'the Destroyer');
    output = output.replace(/\bun\s+ravageur\b/gi, 'a Destroyer');
    output = output.replace(/\bdes\s+ravageurs\b/gi, 'Destroyers');
    output = output.replace(/\bravageurs\b/gi, 'Destroyers');
    output = output.replace(/\bravageur\b/gi, 'Destroyer');

    // Generic mobs expressions
    output = output.replace(/\bfamilles?\s+de\s+(?:monstres?|mobs?)\b/gi, 'monster families');
    output = output.replace(/\bfamille\s+de\s+(?:monstres?|mobs?)\b/gi, 'monster family');
    output = output.replace(/\bclean\s+les\s+mobs\b/gi, 'clear the mobs');
    output = output.replace(/\bpack\s+les\s+mobs\b/gi, 'group the mobs');
    output = output.replace(/\bbloque\s+le\s+mob\b/gi, 'block the mob');
    output = output.replace(/\btacle\s+le\s+mob\b/gi, 'lock the monster');
    output = output.replace(/\bfocus\s+le\s+mob\b/gi, 'focus the monster');
    output = output.replace(/\bles\s+mobs\b/gi, 'the mobs');
    output = output.replace(/\ble\s+mob\b/gi, 'the mob');
    output = output.replace(/\bun\s+mob\b/gi, 'a mob');
    output = output.replace(/\bdes\s+mobs\b/gi, 'mobs');

    for (const entry of combinedEntries) {
      if (!entry.en || !entry.fr || entry.fr.length < 2) continue;
      const candidates = [entry.fr, ...(entry.aliases_fr || [])];
      for (const cand of candidates) {
        if (!cand || cand.length < 2 || cand.includes('?')) continue;
        const candLower = cand.toLowerCase().trim();
        if (GENERIC_CONVERSATIONAL_WORDS.has(candLower)) continue;
        const djRegex = new RegExp(`(?:^|\\b)(?:dj|donjon)(?:\\s+(?:du|de\\s+la|des|de\\s+l['']|d['']|de))?\\s+${escapeRegExp(cand)}(?=\\s|$|[-.,?!/])`, 'gi');
        if (djRegex.test(output)) {
          const dungeonTarget = entry.en.toLowerCase().endsWith('dungeon') ? entry.en : `${entry.en} Dungeon`;
          output = output.replace(djRegex, dungeonTarget);
        }
      }
    }

    output = output.replace(/\bdj\b/gi, 'dungeon');

    const lowerOut = output.toLowerCase();
    const matchedPairs: { cand: string; target: string }[] = [];
    for (const item of combinedEntries) {
      if (item.context_sensitive && !item.fr.includes(' ')) continue;
      const candidates = [item.fr, ...(item.aliases_fr || [])];
      for (const cand of candidates) {
        if (!cand || cand.length < 3) continue;
        const candLow = cand.toLowerCase().trim();
        if (GENERIC_CONVERSATIONAL_WORDS.has(candLow)) continue;
        if (/^(?:niveau|level|nivel|nível)\s+\d+$/i.test(candLow)) continue;
        if (item.context_sensitive && !candLow.includes(' ')) continue;

        if (lowerOut.includes(candLow)) {
          matchedPairs.push({ cand, target: item.en });
        }
      }
    }
    const offlinePlaceholders: { ph: string; target: string }[] = [];
    matchedPairs.sort((a, b) => b.cand.length - a.cand.length);
    for (const pair of matchedPairs) {
      const regex = new RegExp(`(?:^|\\b)${escapeRegExp(pair.cand)}(?=\\s|$|[.,?!])`, 'gi');
      if (regex.test(output)) {
        regex.lastIndex = 0;
        const ph = `__OFFTOK_${offlinePlaceholders.length}__`;
        offlinePlaceholders.push({ ph, target: pair.target });
        output = output.replace(regex, ph);
      }
    }

    if (!matchedQuestion) {
      for (const [pattern, repl] of FR_QUESTION_AND_VERB_PATTERNS) {
        output = output.replace(pattern, repl);
      }
    }

    for (const [pattern, repl] of FR_EN_COMMON_GRAMMAR) {
      output = output.replace(pattern, repl);
    }

    output = output.replace(/\bice\s*creams?\b/gi, 'ice');
    output = output.replace(/\bmy\s+person\b/gi, 'my character');
    output = output.replace(/\bthe\s+DJ\b/g, 'the dungeon');

    // Restore protected entity tokens
    for (let i = offlinePlaceholders.length - 1; i >= 0; i--) {
      output = output.split(offlinePlaceholders[i].ph).join(offlinePlaceholders[i].target);
    }

    output = polishEnglishArticles(output);

    output = output
      .replace(/\s+,/g, ',')
      .replace(/\s+\./g, '.')
      .replace(/\s+!/g, '!')
      .replace(/\s+\?/g, '?')
      .replace(/\s{2,}/g, ' ')
      .trim();

    if (text[0] === text[0].toUpperCase() && output.length > 0) {
      output = output.charAt(0).toUpperCase() + output.slice(1);
    }

    return chatCommandPrefix ? chatCommandPrefix + output : output;
  } else {
    // EN to FR offline translation
    output = output.replace(/\bbounties\b/gi, 'avis de recherche');
    output = output.replace(/\bbounty\b/gi, 'avis de recherche');

    output = output.replace(/\bLF\s+(\d+)\s+spots?\b/gi, 'cherche $1 places');
    output = output.replace(/\bLF\s+(\d+)\s+more\b/gi, 'cherche encore $1');
    output = output.replace(/\bLF\s+(\d+)\s+(?:rox|dps)\b/gi, 'cherche $1 DPS');
    output = output.replace(/\bLF\s+group\b/gi, 'cherche groupe');
    output = output.replace(/\bLF\b/gi, 'cherche');
    output = output.replace(/\b(\d+)\s+spots?\b/gi, '$1 places');
    output = output.replace(/\b(?:a|1)\s+spot\b/gi, '1 place');
    output = output.replace(/\bwho\s+can\s+carry\b/gi, 'qui peut gérer');
    output = output.replace(/\bcan\s+you\s+carry\b/gi, 'tu peux gérer');
    output = output.replace(/\bcarry\b/gi, 'gérer');
    output = output.replace(/\b(?:pm|dm|whisper)\s+me\b/gi, 'mp moi');
    output = output.replace(/\b(?:pm|dm|whisper)\s+offer\b/gi, 'mp offre');
    output = output.replace(/\b(?:pm|dm|whisper)\b/gi, 'mp');
    output = output.replace(/\bWTS\b/gi, 'vends');
    output = output.replace(/\bWTB\b/gi, 'achète');
    output = output.replace(/\bselling\b/gi, 'vends');
    output = output.replace(/\bbuying\b/gi, 'achète');
    output = output.replace(/\bexo\s*ap\b/gi, 'exo PA');
    output = output.replace(/\bexo\s*mp\b/gi, 'exo PM');
    output = output.replace(/\bap\b/gi, 'PA');
    output = output.replace(/\bmp\b/gi, 'PM');
    output = output.replace(/\brange\b/gi, 'PO');
    output = output.replace(/\bmelee\b/gi, 'CAC');
    output = output.replace(/\bmarketplace\b/gi, 'HDV');

    // Dofus monster families & mob expressions (offline en -> fr)
    output = output.replace(/\bthe\s+destroyer\s+mobs\b/gi, 'les mobs Ravageurs');
    output = output.replace(/\bdestroyer\s+mobs\b/gi, 'mobs Ravageurs');
    output = output.replace(/\bthe\s+destroyer\s+mob\b/gi, 'le mob Ravageur');
    output = output.replace(/\ba\s+destroyer\s+mob\b/gi, 'un mob Ravageur');
    output = output.replace(/\bdestroyer\s+mob\b/gi, 'mob Ravageur');
    output = output.replace(/\bthe\s+destroyers\s+family\b/gi, 'la famille des Ravageurs');
    output = output.replace(/\bdestroyers\s+family\b/gi, 'famille des Ravageurs');
    output = output.replace(/\bthe\s+destroyers\b/gi, 'les Ravageurs');
    output = output.replace(/\bthe\s+destroyer\b/gi, 'le Ravageur');
    output = output.replace(/\ba\s+destroyer\b/gi, 'un Ravageur');
    output = output.replace(/\bdestroyers\b/gi, 'Ravageurs');
    output = output.replace(/\bdestroyer\b/gi, 'Ravageur');

    // Generic mobs expressions
    output = output.replace(/\bmonster\s+families\b/gi, 'familles de monstres');
    output = output.replace(/\bmonster\s+family\b/gi, 'famille de monstres');
    output = output.replace(/\bclear\s+the\s+mobs\b/gi, 'clean les mobs');
    output = output.replace(/\bgroup\s+the\s+mobs\b/gi, 'pack les mobs');
    output = output.replace(/\bblock\s+the\s+mob\b/gi, 'bloque le mob');
    output = output.replace(/\block\s+the\s+monster\b/gi, 'tacle le mob');
    output = output.replace(/\bfocus\s+the\s+monster\b/gi, 'focus le mob');
    output = output.replace(/\bthe\s+mobs\b/gi, 'les mobs');
    output = output.replace(/\bthe\s+mob\b/gi, 'le mob');
    output = output.replace(/\ba\s+mob\b/gi, 'un mob');

    for (const entry of combinedEntries) {
      if (!entry.en || !entry.fr || entry.en.length < 2) continue;
      const djEnRegex = new RegExp(`(?:^|\\b)${escapeRegExp(entry.en)}\\s+dungeon(?=\\s|$|[-.,?!/])`, 'gi');
      if (djEnRegex.test(output)) {
        output = output.replace(djEnRegex, `donjon ${entry.fr}`);
      }
    }

    for (const [pattern, repl] of EN_FR_COMMON_GRAMMAR) {
      output = output.replace(pattern, repl);
    }

    output = output.replace(/\bles\s+des\s+mobs\b/gi, 'les mobs');
    output = output.replace(/\bclean\s+les\s+des\s+mobs\b/gi, 'clean les mobs');
    output = output.replace(/\bdes\s+mobs\s+Ravageurs\b/gi, 'mobs Ravageurs');

    for (const [pattern, repl] of DOFUS_CHAT_IDIOMS_EN_TO_FR) {
      output = output.replace(pattern, repl);
    }

    for (const [frZone, enZone] of Object.entries(DOFUS_DIMENSIONS_AND_ZONES)) {
      if (!output.toLowerCase().includes(enZone.toLowerCase())) continue;
      const regex = new RegExp(`\\b${escapeRegExp(enZone)}\\b`, 'gi');
      output = output.replace(regex, frZone);
    }

    for (const [frMob, enMob] of Object.entries(DOFUS_ARCHIMONSTERS_AND_WANTED)) {
      if (!output.toLowerCase().includes(enMob.toLowerCase())) continue;
      const regex = new RegExp(`\\b${escapeRegExp(enMob)}\\b`, 'gi');
      output = output.replace(regex, frMob);
    }

    for (const [frClass, info] of Object.entries(DOFUS_CLASSES_FR_EN)) {
      if (!output.toLowerCase().includes(info.en.toLowerCase())) continue;
      const regex = new RegExp(`\\b${escapeRegExp(info.en)}\\b`, 'gi');
      output = output.replace(regex, frClass);
    }

    const lowerOut = output.toLowerCase();
    const matchedPairs: { cand: string; target: string }[] = [];
    for (const item of combinedEntries) {
      if (!item.en || item.en.length < 2) continue;
      const enLow = item.en.toLowerCase().trim();
      if (GENERIC_CONVERSATIONAL_WORDS.has(enLow)) continue;
      if (lowerOut.includes(enLow)) {
        matchedPairs.push({ cand: item.en, target: item.fr });
      }
    }
    matchedPairs.sort((a, b) => b.cand.length - a.cand.length);
    for (const pair of matchedPairs) {
      const regex = new RegExp(`(?:^|\\b)${escapeRegExp(pair.cand)}(?=\\s|$|[.,?!])`, 'gi');
      output = output.replace(regex, pair.target);
    }

    for (const [pattern, repl] of EN_FR_COMMON_GRAMMAR) {
      output = output.replace(pattern, repl);
    }

    output = output.replace(/\bles\s+des\s+mobs\b/gi, 'les mobs');
    output = output.replace(/\bclean\s+les\s+des\s+mobs\b/gi, 'clean les mobs');
    output = output.replace(/\bdes\s+mobs\s+Ravageurs\b/gi, 'mobs Ravageurs');

    output = output
      .replace(/\s+,/g, ',')
      .replace(/\s+\./g, '.')
      .replace(/\s+!/g, '!')
      .replace(/\s+\?/g, '?')
      .replace(/\s{2,}/g, ' ')
      .trim();

    if (text[0] === text[0].toUpperCase() && output.length > 0) {
      output = output.charAt(0).toUpperCase() + output.slice(1);
    }

    return chatCommandPrefix ? chatCommandPrefix + output : output;
  }
}
