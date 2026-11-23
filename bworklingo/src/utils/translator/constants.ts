import { NotableBossToken, NotableMonsterFamilyToken } from './types';

export function escapeRegExp(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Words that are part of everyday grammar or generic conversation and must NEVER
 * be hijacked by single-word Dofus dictionary items/attitudes/categories outside of [...] brackets.
 */
export const GENERIC_CONVERSATIONAL_WORDS = new Set([
  // French grammar & prepositions (prevents "de" -> "Dice", "mais" -> "Corn", "or" -> "Gold", "sans" -> "No-Face", "grand" -> "King Kongoku")
  'de', 'dé', 'du', 'des', 'le', 'la', 'les', 'un', 'une', 'ou', 'où', 'et', 'est', 'es', 'en', 'au', 'aux',
  'on', 'tu', 'je', 'il', 'ils', 'elle', 'elles', 'nous', 'vous', 'ce', 'cet', 'cette', 'ces', 'se', 'sa', 'son', 'ses',
  'ma', 'mon', 'mes', 'ta', 'ton', 'tes', 'ne', 'ni', 'si', 'va', 'vas', 'vais', 'as', 'ai', 'a', 'à', 'an', 'ans',
  'os', 'or', 'par', 'sur', 'sous', 'dans', 'avec', 'sans', 'pour', 'vers', 'chez', 'mais', 'donc', 'car', 'qui', 'que',
  'quoi', 'dont', 'pas', 'plus', 'tout', 'tous', 'toute', 'toutes', 'rien', 'bien', 'mal', 'peu', 'très', 'tres',
  'bon', 'bonne', 'beau', 'belle', 'grand', 'petit', 'même', 'meme', 'autre', 'autres', 'ici', 'là',
  'oui', 'non', 'moi', 'toi', 'lui', 'eux', 'leur', 'leurs', 'notre', 'votre', 'nos', 'vos', 'été', 'ete', 'fait',
  'fais', 'faire', 'dit', 'dire', 'mis', 'pris', 'vu', 'su', 'pu', 'dû', 'eu', 'avoir', 'être', 'etre',
  // Generic single-word nouns/verbs that neural translation handles better in sentence context
  'niveau', 'level', 'nivel', 'nível', 'force', 'chance', 'terre', 'eau', 'air', 'feu', 'état', 'etat',
  'fuite', 'soins', 'renvoi', 'portée', 'portee', 'recrute', 'cherche', 'achète', 'achete', 'vends', 'vend',
  'combat', 'expérience', 'experience', 'xp', 'pano', 'salut', 'bonjour', 'merci', 'attend', 'attends',
  'aide', 'besoin', 'dispo', 'disponible', 'saluer', 'rire', 'danser', 'joie', 'fleurs', 'coucou', 'calmer',
  'huer', 'écrire', 'ecrire', 'boxer', 'rugir', 'animal', 'rêve', 'reve', 'parer', 'accord', 'trace',
  'quêtes', 'quetes', 'donjons', 'guilde', 'métiers', 'metiers', 'élevage', 'elevage', 'succès', 'succes',
  'monstres', 'général', 'general', 'pierre', 'plume', 'fer', 'cuivre', 'bois', 'blé', 'ble',
  'fou', 'peur', 'bond', 'mine', 'lac', 'base', 'sort', 'sac', 'pain', 'sel', 'solo', 'duo', 'trio', 'duel',
  'mort', 'fin', 'chef', 'roi', 'fille', 'fils', 'avis',
  "s'il vous plait", "s'il vous plaît", "s'il te plait", "s'il te plaît",
  // English / Spanish / Portuguese prepositions, pronouns & basic verbs
  'the', 'and', 'for', 'are', 'am', 'is', 'be', 'do', 'so', 'to', 'at', 'it', 'in', 'on', 'by', 'if', 'as', 'my', 'we', 'he', 'me', 'us', 'but', 'not', 'you', 'all', 'any', 'can', 'with', 'from', 'have', 'this', 'that',
  'el', 'los', 'las', 'del', 'al', 'con', 'sin', 'por', 'para', 'como', 'más', 'mas', 'pero', 'sus', 'mis', 'tus', 'uno', 'una', 'hola', 'busco', 'vendo', 'compro', 'llave', 'llaves', 'plaza', 'plazas', 'grupo', 'gracias',
  'em', 'no', 'na', 'nos', 'nas', 'do', 'da', 'dos', 'das', 'ao', 'aos', 'com', 'sem', 'mais', 'meu', 'seu', 'sua', 'um', 'uma', 'quem', 'olá', 'ola', 'procuro', 'chave', 'chaves', 'vaga', 'vagas', 'obrigado'
]);

// 4-language token definitions for key Dofus bosses commonly referenced by players
export const NOTABLE_BOSS_TOKENS: NotableBossToken[] = [
  { fr: 'Comte Harebourg', en: 'Count Harebourg', es: 'Conde Kontatrás', pt: 'Conde Traspafrent', terms: ['comte harebourg', 'count harebourg', 'conde kontatrás', 'conde kontatras', 'conde traspafrent', 'comte', 'harebourg', 'kontatras', 'konta', 'traspafrent'] },
  { fr: 'Roi Nidas', en: 'King Nidas', es: 'Rey Nidas', pt: 'Rei Nidas', terms: ['roi nidas', 'king nidas', 'rey nidas', 'rei nidas', 'nidas'] },
  { fr: 'Reine des Voleurs', en: 'Queen of Thieves', es: 'Reina de los Ladrones', pt: 'Rainha dos Ladrões', terms: ['reine des voleurs', 'queen of thieves', 'reina de los ladrones', 'rainha dos ladrões', 'rainha dos ladroes'] },
  { fr: 'Korriandre', en: 'Korriander', es: 'Cil', pt: 'Kwentro', terms: ['korriandre', 'korriander', 'korri', 'kwentro'] },
  { fr: 'Glourséleste', en: 'Celestial Bearbarian', es: 'Golosotrón Real', pt: 'Glurseleste', terms: ['glourséleste', 'glourseleste', 'celestial bearbarian', 'golosotrón real', 'golosotron real', 'golosotron', 'glurseleste', 'glours'] },
  { fr: 'Missiz Freezz', en: 'Missiz Freezz', es: 'Mizz Frizz', pt: 'Missiz Frizz', terms: ['missiz freezz', 'missiz frizz', 'mizz frizz', 'missiz', 'mf'] },
  { fr: 'Ilyzaelle', en: 'Ilyzaelle', es: 'Ilyzaelle', pt: 'Ilyzaelle', terms: ['ilyzaelle', 'ily'] },
  { fr: 'Protozreur', en: 'Protozorror', es: 'Protozorror', pt: 'Protozorror', terms: ['protozreur', 'protozorror', 'proto'] },
  { fr: 'Chaloeil', en: 'Catseye', es: 'Ojo de Buey', pt: 'Olho de Boi', terms: ['chaloeil', 'catseye', 'ojo de buey', 'olho de boi'] },
  { fr: 'Koutoulou', en: 'Captain Koutoulou', es: 'Capitán Kutulú', pt: 'Capitão Cthulhu', terms: ['koutoulou', 'captain koutoulou', 'capitán kutulú', 'capitan kutulu', 'capitão cthulhu', 'capitao cthulhu'] },
  { fr: 'Meno', en: 'Captain Meno', es: 'Capitán Meno', pt: 'Capitão Meno', terms: ['capitaine meno', 'captain meno', 'capitán meno', 'capitan meno', 'capitão meno', 'capitao meno', 'meno'] },
  { fr: 'Belladone', en: 'Belladonna', es: 'Belladona', pt: 'Beladona', terms: ['belladone', 'belladonna', 'belladona', 'beladona', 'bella'] },
  { fr: 'Torkélonia', en: 'Torkelonia', es: 'Torkelonia', pt: 'Torkelônia', terms: ['torkélonia', 'torkelonia', 'torkelônia', 'torke'] },
  { fr: 'Cire Momore', en: 'Cire Momore', es: 'Cera Momore', pt: 'Cera Momore', terms: ['cire momore', 'cera momore', 'cire'] },
  { fr: 'Dragon Cochon', en: 'Dragon Pig', es: 'Dragocerdo', pt: 'Dragão-Porco', terms: ['dragon cochon', 'dragon pig', 'dragocerdo', 'dragão-porco', 'dragao-porco', 'dragao porco', 'dc'] },
  { fr: 'Chêne Mou', en: 'Soft Oak', es: 'Roble Blando', pt: 'Carvalho Mole', terms: ['chêne mou', 'chene mou', 'soft oak', 'roble blando', 'roble', 'carvalho mole', 'cm'] },
  { fr: 'Bouftou Royal', en: 'Royal Gobball', es: 'Jalató Real', pt: 'Papatudo Real', terms: ['bouftou royal', 'royal gobball', 'jalató real', 'jalato real', 'papatudo real', 'br'] },
  { fr: 'Royalmouth', en: 'Royal Mastogob', es: 'Jalamut Real', pt: 'Papatudo da Neve Real', terms: ['royalmouth', 'royal mastogob', 'jalamut real', 'papatudo da neve real', 'rm'] },
  { fr: 'Gourlo le Terrible', en: 'Gourlo the Terrible', es: 'Gourlo el Terrible', pt: 'Gourlo, o Terrível', terms: ['gourlo le terrible', 'gourlot le terrible', 'gourlo the terrible', 'gourlo el terrible', 'gourlo, o terrível', 'gourlo', 'gourlot'] },
  { fr: 'Rat Noir', en: 'Black Rat', es: 'Rata Negra', pt: 'Rato Negro', terms: ['rat noir', 'black rat', 'rata negra', 'rato negro', 'rn'] },
  { fr: 'Rat Blanc', en: 'White Rat', es: 'Rata Blanca', pt: 'Rato Branco', terms: ['rat blanc', 'white rat', 'rata blanca', 'rato branco', 'rb'] },
  { fr: 'Crocabulia', en: 'Crocabulia', es: 'Crocabulia', pt: 'Crocabulia', terms: ['crocabulia', 'croca'] },
  { fr: 'Rasboul Majeur', en: 'Silf the Rasboul Major', es: 'Rasgabola Mayor', pt: 'Rasgabul Maior', terms: ['rasboul majeur', 'rasboul', 'silf le rasboul majeur', 'rasgabola mayor', 'rasgabul maior'] },
  { fr: 'Kimbo', en: 'Kimbo', es: 'Kimbo', pt: 'Kimbo', terms: ['kimbo'] },
  { fr: 'Bworker', en: 'Bworker', es: 'Bworker', pt: 'Bworker', terms: ['bworker'] },
  { fr: 'Skeunk', en: 'Skeunk', es: 'Skunk', pt: 'Skeunk', terms: ['skeunk'] },
  { fr: 'Dantinéa', en: 'Dantineea', es: 'Dantinea', pt: 'Dantínea', terms: ['dantinéa', 'dantinea', 'dantínea', 'dantineea', 'danti'] },
  { fr: 'Solar', en: 'Solar', es: 'Solar', pt: 'Solar', terms: ['solar'] },
  { fr: 'Bethel Akarna', en: 'Bethel Akarna', es: 'Bethel Akarna', pt: 'Bethel Akarna', terms: ['bethel akarna', 'bethel'] },
  { fr: 'Servitude', en: 'Servitude', es: 'Servidumbre', pt: 'Servidão', terms: ['servitude', 'servidumbre', 'servidão', 'servidao'] },
  { fr: 'Misère', en: 'Misery', es: 'Miseria', pt: 'Miséria', terms: ['misère', 'misere', 'miseria', 'miséria'] },
  { fr: 'Guerre', en: 'War', es: 'Guerra', pt: 'Guerra', terms: ['guerre', 'guerra'] },
  { fr: 'Corruption', en: 'Corruption', es: 'Corrupción', pt: 'Corrupção', terms: ['corruption', 'corrupción', 'corrupcion', 'corrupção', 'corrupcao'] },
  { fr: 'Meulou', en: 'Moowolf', es: 'Maxilubo', pt: 'Mulobo', terms: ['meulou', 'moowolf', 'maxilubo', 'mulobo'] },
  { fr: 'Kralamoure géant', en: 'Giant Kralove', es: 'Kralamar Gigante', pt: 'Kralamor Gigante', terms: ['kralamoure géant', 'kralamoure geant', 'giant kralove', 'kralamar gigante', 'kralamor gigante', 'kralamoure', 'kralamour', 'kralamar', 'kralamor', 'krala'] },
  { fr: 'Sphincter Cell', en: 'Sphincter Cell', es: 'Esfínter Cell', pt: 'Esfíncter Cell', terms: ['sphincter cell', 'esfínter cell', 'esfinter cell', 'esfíncter cell', 'sphincter'] },
  { fr: 'Ougah', en: 'Ougah', es: 'Ugah', pt: 'Ugah', terms: ['ougah', 'ugah'] },
  { fr: 'Tengu Givrefoux', en: 'Tengu Snowfoux', es: 'Tengu Gélifux', pt: 'Tengu Gelifox', terms: ['tengu givrefoux', 'tengu snowfoux', 'tengu gélifux', 'tengu gelifux', 'tengu gelifox', 'tengu'] },
  { fr: 'Fuji Givrefoux', en: 'Foster Fuji Snowfoux', es: 'Fuji Gélifux Nodriza', pt: 'Fuji Gelifox Maternal', terms: ['fuji givrefoux', 'fuji givrefoux nourriciere', 'fuji gélifux nodriza', 'fuji gelifox maternal', 'fuji'] }
];

// 4-language token definitions for key Dofus monster families commonly referenced in chat / recruitment
// Distinguishes singular & plural so "un ravageur" -> "a Destroyer" and "des ravageurs" -> "Destroyers"
export const NOTABLE_MONSTER_FAMILIES_TOKENS: NotableMonsterFamilyToken[] = [
  {
    plural: { fr: 'Ravageurs', en: 'Destroyers', es: 'Devastadores', pt: 'Devastadores', terms: ['ravageurs', 'destroyers', 'devastadores'] },
    singular: { fr: 'Ravageur', en: 'Destroyer', es: 'Devastador', pt: 'Devastador', terms: ['ravageur', 'destroyer', 'devastador'] }
  },
  {
    plural: { fr: 'Gloursons', en: 'Bearbarians', es: 'Golosotes', pt: 'Ursóbaros', terms: ['gloursons', 'bearbarians', 'golosotes', 'ursóbaros', 'ursobaros'] },
    singular: { fr: 'Glourson', en: 'Bearbarian', es: 'Golosote', pt: 'Ursóbaro', terms: ['glourson', 'bearbarian', 'golosote', 'ursóbaro', 'ursobaro'] }
  },
  {
    plural: { fr: 'Mansots', en: 'Pingwins', es: 'Pájaros del tiempo', pt: 'Pinguins', terms: ['mansots', 'pingwins', 'pingüinos', 'pinguinos', 'pinguins'] },
    singular: { fr: 'Mansot', en: 'Pingwin', es: 'Pájaro del tiempo', pt: 'Pinguim', terms: ['mansot', 'pingwin', 'pingüino', 'pinguino', 'pinguim'] }
  },
  {
    plural: { fr: 'Boufmouths', en: 'Mastogobs', es: 'Jalamuts', pt: 'Papatudos da Neve', terms: ['boufmouths', 'mastogobs', 'jalamuts', 'papatudos da neve'] },
    singular: { fr: 'Boufmouth', en: 'Mastogob', es: 'Jalamut', pt: 'Papatudo da Neve', terms: ['boufmouth', 'mastogob', 'jalamut', 'papatudo da neve'] }
  },
  {
    plural: { fr: 'Givrefoux', en: 'Snowfoux', es: 'Gélifux', pt: 'Raposaneves', terms: ['givrefoux', 'snowfoux', 'gélifux', 'gelifux', 'raposaneves'] },
    singular: { fr: 'Givrefoux', en: 'Snowfoux', es: 'Gélifux', pt: 'Raposaneves', terms: ['givrefoux', 'snowfoux', 'gélifux', 'gelifux', 'raposaneves'] }
  },
  {
    plural: { fr: 'Craqueleurs', en: 'Cracklers', es: 'Crujidores', pt: 'Cracleres', terms: ['craqueleurs', 'cracklers', 'crujidores', 'cracleres'] },
    singular: { fr: 'Craqueleur', en: 'Crackler', es: 'Crujidor', pt: 'Craclere', terms: ['craqueleur', 'crackler', 'crujidor', 'cracler'] }
  },
  {
    plural: { fr: 'Abraknydes', en: 'Treechnids', es: 'Abraknidos', pt: 'Treechnids', terms: ['abraknydes', 'treechnids', 'abraknidos'] },
    singular: { fr: 'Abraknyde', en: 'Treechnid', es: 'Abraknido', pt: 'Treechnid', terms: ['abraknyde', 'treechnid', 'abraknido'] }
  },
  {
    plural: { fr: 'Mulous', en: 'Boowolves', es: 'Mulus', pt: 'Mulobos', terms: ['mulous', 'boowolves', 'mulus', 'mulobos'] },
    singular: { fr: 'Mulou', en: 'Boowolf', es: 'Mulu', pt: 'Mulobo', terms: ['mulou', 'boowolf', 'mulobo'] }
  },
  {
    plural: { fr: 'Dragoeufs', en: 'Dreggons', es: 'Dragohuevos', pt: 'Dragovos', terms: ['dragoeufs', 'dreggons', 'dragohuevos', 'dragovos'] },
    singular: { fr: 'Dragoeuf', en: 'Dreggon', es: 'Dragohuevo', pt: 'Dragovo', terms: ['dragoeuf', 'dreggon', 'dragohuevo', 'dragovo'] }
  },
  {
    plural: { fr: 'Scarafeuilles', en: 'Scaraleaves', es: 'Escarahojas', pt: 'Escarafolhas', terms: ['scarafeuilles', 'scaraleaves', 'escarahojas', 'escarafolhas', 'scaras'] },
    singular: { fr: 'Scarafeuille', en: 'Scaraleaf', es: 'Escarahoja', pt: 'Escarafolha', terms: ['scarafeuille', 'scaraleaf', 'escarahoja', 'escarafolha', 'scara'] }
  },
  {
    plural: { fr: 'Pious', en: 'Piwis', es: 'Píos', pt: 'Pius', terms: ['pious', 'piwis', 'píos', 'pios', 'pius'] },
    singular: { fr: 'Piou', en: 'Piwi', es: 'Pío', pt: 'Piu', terms: ['piou', 'piwi', 'pío', 'pio', 'piu'] }
  },
  {
    plural: { fr: 'Crocodailles', en: 'Crocodyls', es: 'Cocodriluchos', pt: 'Crocodilos', terms: ['crocodailles', 'crocodyls', 'cocodriluchos', 'crocodilos'] },
    singular: { fr: 'Crocodaille', en: 'Crocodyl', es: 'Cocodrilucho', pt: 'Crocodilo', terms: ['crocodaille', 'crocodyl', 'cocodrilucho', 'crocodilo'] }
  },
  {
    plural: { fr: 'Trithons', en: 'Trituns', es: 'Tritones', pt: 'Tritões', terms: ['trithons', 'trituns', 'tritones', 'tritões', 'tritoes'] },
    singular: { fr: 'Trithon', en: 'Tritun', es: 'Tritón', pt: 'Tritão', terms: ['trithon', 'tritun', 'tritón', 'triton', 'tritão', 'tritao'] }
  },
  {
    plural: { fr: 'Égarés', en: 'Fugitives', es: 'Extraviados', pt: 'Perdidos', terms: ['égarés', 'egares', 'fugitives', 'extraviados', 'perdidos'] },
    singular: { fr: 'Égaré', en: 'Fugitive', es: 'Extraviado', pt: 'Perdido', terms: ['égaré', 'egare', 'fugitive', 'extraviado', 'perdido'] }
  },
  {
    plural: { fr: 'Gourgloutons', en: 'Gluttons', es: 'Tragaldabas', pt: 'Gourgloutons', terms: ['gourgloutons', 'gluttons', 'tragaldabas'] },
    singular: { fr: 'Gourglouton', en: 'Glutton', es: 'Tragaldaba', pt: 'Gourglouton', terms: ['gourglouton', 'glutton', 'tragaldaba'] }
  },
  {
    plural: { fr: 'Nécronyx', en: 'Necronyx', es: 'Necrónix', pt: 'Necronyx', terms: ['nécronyx', 'necronyx', 'necrónix', 'necronix'] },
    singular: { fr: 'Nécronyx', en: 'Necronyx', es: 'Necrónix', pt: 'Necronyx', terms: ['nécronyx', 'necronyx', 'necrónix', 'necronix'] }
  },
  {
    plural: { fr: 'Gelées', en: 'Jellies', es: 'Gelatinas', pt: 'Geléias', terms: ['gelées', 'gelees', 'jellies', 'gelatinas', 'geléias', 'geleias'] },
    singular: { fr: 'Gelée', en: 'Jelly', es: 'Gelatina', pt: 'Geléia', terms: ['gelée', 'gelee', 'jelly', 'gelatina', 'geléia', 'geleia'] }
  },
  {
    plural: { fr: 'Porkass', en: 'Lousy Pigs', es: 'Porkass', pt: 'Porkass', terms: ['porkass', 'lousy pigs'] },
    singular: { fr: 'Porkass', en: 'Lousy Pig', es: 'Porkass', pt: 'Porkass', terms: ['porkass', 'lousy pig'] }
  },
  {
    plural: { fr: 'Kanigs', en: 'Kanigs', es: 'Kanigs', pt: 'Kanigs', terms: ['kanigs', 'kanigrous', 'kanigers', 'kanigrus'] },
    singular: { fr: 'Kanig', en: 'Kanig', es: 'Kanig', pt: 'Kanig', terms: ['kanig', 'kanigrou', 'kaniger', 'kanigru'] }
  },
  {
    plural: { fr: 'Chafers', en: 'Chafers', es: 'Chafers', pt: 'Chafers', terms: ['chafers'] },
    singular: { fr: 'Chafer', en: 'Chafer', es: 'Chafer', pt: 'Chafer', terms: ['chafer'] }
  },
  {
    plural: { fr: 'Bworks', en: 'Bworks', es: 'Bworks', pt: 'Bworks', terms: ['bworks'] },
    singular: { fr: 'Bwork', en: 'Bwork', es: 'Bwork', pt: 'Bwork', terms: ['bwork'] }
  },
  {
    plural: { fr: 'Wabbits', en: 'Wabbits', es: 'Wabbits', pt: 'Wabbits', terms: ['wabbits'] },
    singular: { fr: 'Wabbit', en: 'Wabbit', es: 'Wabbit', pt: 'Wabbit', terms: ['wabbit'] }
  },
  {
    plural: { fr: 'Koalaks', en: 'Koalaks', es: 'Koalaks', pt: 'Koalaks', terms: ['koalaks'] },
    singular: { fr: 'Koalak', en: 'Koalak', es: 'Koalak', pt: 'Koalak', terms: ['koalak'] }
  },
  {
    plural: { fr: 'Dopeuls', en: 'Dopples', es: 'Dopeuls', pt: 'Dopeuls', terms: ['dopeuls', 'dopples'] },
    singular: { fr: 'Dopeul', en: 'Dopple', es: 'Dopeul', pt: 'Dopeul', terms: ['dopeul', 'dopple'] }
  },
  {
    plural: { fr: 'Bouftous', en: 'Gobballs', es: 'Jalatós', pt: 'Papatudos', terms: ['bouftous', 'gobballs', 'jalatós', 'jalatos', 'papatudos'] },
    singular: { fr: 'Bouftou', en: 'Gobball', es: 'Jalató', pt: 'Papatudo', terms: ['bouftou', 'gobball', 'jalató', 'jalato', 'papatudo'] }
  },
  {
    plural: { fr: 'Tofus', en: 'Tofus', es: 'Tofus', pt: 'Tofus', terms: ['tofus'] },
    singular: { fr: 'Tofu', en: 'Tofu', es: 'Tofu', pt: 'Tofu', terms: ['tofu'] }
  },
  {
    plural: { fr: 'Larves', en: 'Larvae', es: 'Larvas', pt: 'Larvas', terms: ['larves', 'larvae', 'larvas'] },
    singular: { fr: 'Larve', en: 'Larva', es: 'Larva', pt: 'Larva', terms: ['larve', 'larva'] }
  },
  {
    plural: { fr: 'Blops', en: 'Blops', es: 'Blops', pt: 'Blops', terms: ['blops'] },
    singular: { fr: 'Blop', en: 'Blop', es: 'Blop', pt: 'Blop', terms: ['blop'] }
  },
  {
    plural: { fr: 'Corbacs', en: 'Crows', es: 'Cuerboks', pt: 'Korbaks', terms: ['corbacs', 'crows', 'cuerboks', 'korbaks'] },
    singular: { fr: 'Corbac', en: 'Crow', es: 'Cuerbok', pt: 'Korbak', terms: ['corbac', 'crow', 'cuerbok', 'korbak'] }
  },
  {
    plural: { fr: 'Prespics', en: 'Prespics', es: 'Prespics', pt: 'Prespics', terms: ['prespics'] },
    singular: { fr: 'Prespic', en: 'Prespic', es: 'Prespic', pt: 'Prespic', terms: ['prespic'] }
  }
];
