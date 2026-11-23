/**
 * Normalizes common French video game chat typos, SMS spelling, and spacing
 * strictly into standard French (never injects other languages).
 */
export function normalizeFrenchGamingChat(text: string): string {
  if (!text) return '';

  let t = text;

  // Separate numbers stuck to units like "4/6minutes" -> "4/6 minutes"
  t = t.replace(/(\d+)\s*(minutes?|mins?|heures?|tours?|combats?)\b/gi, '$1 $2');

  // Verb conjugations & phonetic endings
  t = t.replace(/(?:^|\b)on\s+(?:f[eéèê]+|fai[st]?)(?=\s|$|[.,?!])/gi, 'on fait');
  t = t.replace(/(?:^|\b)tu\s+(?:f[eéèê]+|fai[st]?)(?=\s|$|[.,?!])/gi, 'tu fais');
  t = t.replace(/(?:^|\b)je\s+(?:f[eéèê]+|fai[st]?)(?=\s|$|[.,?!])/gi, 'je fais');
  t = t.replace(/(?:^|\b)(?:ki|qui)\s+(?:f[eéèê]+|fai[st]?)(?=\s|$|[.,?!])/gi, 'qui fait');
  t = t.replace(/(?:^|\b)il\s+(?:f[eéèê]+|fai[st]?)(?=\s|$|[.,?!])/gi, 'il fait');

  t = t.replace(/(?:^|\b)tu\s+(?:vien[dt]?)(?=\s|$|[.,?!])/gi, 'tu viens');
  t = t.replace(/(?:^|\b)je\s+(?:vien[dt]?)(?=\s|$|[.,?!])/gi, 'je viens');
  t = t.replace(/(?:^|\b)on\s+(?:vien[dt]?)(?=\s|$|[.,?!])/gi, 'on vient');
  t = t.replace(/(?:^|\b)(?:ki|qui)\s+(?:vien[dt]?)(?=\s|$|[.,?!])/gi, 'qui vient');

  t = t.replace(/(?:^|\b)(?:ki|qui)\s+(?:veu[tx]?|ve)(?=\s|$|[.,?!])/gi, 'qui veut');
  t = t.replace(/(?:^|\b)tu\s+(?:veu[tx]?|ve)(?=\s|$|[.,?!])/gi, 'tu veux');
  t = t.replace(/(?:^|\b)on\s+(?:veu[tx]?|ve)(?=\s|$|[.,?!])/gi, 'on veut');
  t = t.replace(/(?:^|\b)je\s+(?:veu[tx]?|ve)(?=\s|$|[.,?!])/gi, 'je veux');

  t = t.replace(/(?:^|\b)(?:ki|qui)\s+(?:peu[tx]?|pe)(?=\s|$|[.,?!])/gi, 'qui peut');
  t = t.replace(/(?:^|\b)on\s+(?:peu[tx]?|pe)(?=\s|$|[.,?!])/gi, 'on peut');
  t = t.replace(/(?:^|\b)tu\s+(?:peu[tx]?|pe)(?=\s|$|[.,?!])/gi, 'tu peux');
  t = t.replace(/(?:^|\b)je\s+(?:peu[tx]?|pe)(?=\s|$|[.,?!])/gi, 'je peux');

  t = t.replace(/(?:^|\b)(?:ki|qui)\s+(?:g[eéèê]re[st]?)(?=\s|$|[.,?!])/gi, 'qui gère');
  t = t.replace(/(?:^|\b)tu\s+(?:g[eéèê]re[st]?)(?=\s|$|[.,?!])/gi, 'tu gères');
  t = t.replace(/(?:^|\b)on\s+(?:g[eéèê]re[st]?)(?=\s|$|[.,?!])/gi, 'on gère');
  t = t.replace(/(?:^|\b)je\s+(?:g[eéèê]re[st]?)(?=\s|$|[.,?!])/gi, 'je gère');

  // "cv" / "ca va" typo -> "ça va"
  t = t.replace(/\bcv\b/gi, 'ça va');
  t = t.replace(/\b(?:sa\s+va|ca\s+va)\b/gi, 'ça va');
  t = t.replace(/\bdaide\b/gi, "d'aide");

  // Frigost zones
  t = t.replace(/\b(?:fri\s*3|f3)\b/gi, 'Frigost 3');
  t = t.replace(/\b(?:fri\s*2|f2)\b/gi, 'Frigost 2');
  t = t.replace(/\b(?:fri\s*1|f1)\b/gi, 'Frigost 1');

  // Common Dofus abbreviations -> clean French
  t = t.replace(/\b(?:rox+s?|roxeurs?|roxxeurs?)\b/gi, 'DPS');
  t = t.replace(/\bcbt\b/gi, 'combat');
  t = t.replace(/\bfull\s+sasa\b/gi, 'panoplie sagesse');
  t = t.replace(/\b(?:pano|panoplie)\s+bouf\b/gi, 'panoplie Bouftou');
  t = t.replace(/\b(?:pano|panoplie)\s+br\b/gi, 'panoplie Bouftou Royal');
  t = t.replace(/\b(?:pano|panoplie)\s+meulou\b/gi, 'panoplie Meulou');
  t = t.replace(/\b(?:pano|panoplie)\s+cm\b/gi, 'panoplie Chêne Mou');
  t = t.replace(/\b(?:pano|panoplie)\s+piou\b/gi, 'panoplie Piou');
  t = t.replace(/\b(?:pano|panoplie)\s+gel[eé]e\b/gi, 'panoplie Gelée');
  t = t.replace(/\b(?:pano|panoplie)\s+dofus\b/gi, 'panoplie Dofus');
  t = t.replace(/\bpano\b/gi, 'panoplie');
  t = t.replace(/\bpack\s+archis?\b/gi, 'pack archimonstres');
  t = t.replace(/\barchis?\b/gi, 'archimonstres');
  t = t.replace(/\bdispo\b/gi, 'disponible');
  t = t.replace(/\b(?:lv+l|niv)\b/gi, 'niveau');
  t = t.replace(/\b(?:svp)\b/gi, "s'il vous plaît");
  t = t.replace(/\b(?:stp)\b/gi, "s'il te plaît");
  t = t.replace(/\b(?:slt)\b/gi, 'salut');
  t = t.replace(/\b(?:bjr)\b/gi, 'bonjour');
  t = t.replace(/\b(?:chui|chuis|jsuis|jss)\b/gi, 'je suis');
  t = t.replace(/\bj'sui[st]?\b/gi, 'je suis');
  t = t.replace(/\bt'es\b/gi, 'tu es');
  t = t.replace(/\b(?:kelkun|kelk1|qqun|qqn)\b/gi, "quelqu'un");
  t = t.replace(/\b(?:ds|dan)\b/gi, 'dans');
  t = t.replace(/\bpr\b/gi, 'pour');
  t = t.replace(/\bki\b/gi, 'qui');
  t = t.replace(/\bkoi\b/gi, 'quoi');
  t = t.replace(/\bpk\b/gi, 'pourquoi');
  t = t.replace(/\bbcp\b/gi, 'beaucoup');
  t = t.replace(/\b(?:succ[eéèê]s?|sucez|succé)\b/gi, 'succès');
  t = t.replace(/\bg\s+(drop|fini|besoin|trouve|trouvé|perdu|win|gagné)\b/gi, "j'ai $1");
  t = t.replace(/\bc\s+bon\b/gi, "c'est bon");
  t = t.replace(/\bc\s+mort\b/gi, "c'est mort");
  t = t.replace(/\bc\s+chaud\b/gi, "c'est chaud");
  t = t.replace(/\bc\s+parti\b/gi, "c'est parti");
  t = t.replace(/\b(?:sa|ca)\s+vaut\s+combien\b/gi, 'combien ça vaut');
  t = t.replace(/\bcombien\s+(?:sa|ca)\s+c[oô]ute\b/gi, 'combien ça coûte');
  t = t.replace(/\b(?:tkt|tktb)\b/gi, "t'inquiète");
  t = t.replace(/\bdsl\b/gi, 'désolé');
  t = t.replace(/\b(?:mrc|cimer)\b/gi, 'merci');
  t = t.replace(/\b(?:osef|balek)\b/gi, "on s'en fout");
  t = t.replace(/\b(?:jpp)\b/gi, "j'en peux plus");
  t = t.replace(/\b(?:ajd|auj)\b/gi, "aujourd'hui");
  t = t.replace(/\btt\s+de\s+suite\b/gi, 'tout de suite');
  t = t.replace(/\btlm\b/gi, 'tout le monde');

  // "glaces" / "glace" typos for places in recruitment
  t = t.replace(/\b(\d+)\s+glaces?\b/gi, '$1 places');
  t = t.replace(/\b(?:une?|1)\s+glace\b/gi, '1 place');
  t = t.replace(/\bglaces?\s+(dispo|disponible|libre|restante?s?)/gi, 'places $1');
  t = t.replace(/\b(?:cherche|recrute|reste|prends?|trouve)\s+(?:une?|\d+)?\s*glaces?\b/gi, (match) => match.replace(/glaces?/i, 'places'));
  t = t.replace(/\bderni[eè]re\s+glace\b/gi, 'dernière place');

  // Environment ice dungeons
  t = t.replace(/\b(?:dj|donjon)\s+glaces?\b/gi, 'donjon de glace');
  t = t.replace(/\bzone\s+glaces?\b/gi, 'zone de glace');
  t = t.replace(/\bchamps?\s+de\s+glaces?\b/gi, 'champs de glace');
  t = t.replace(/\bîle\s+des\s+glaces?\b/gi, 'île des glaces');

  // "perso" -> "personnage"
  t = t.replace(/\b(mon|ton|son|notre|votre|leur)\s+perso\b/gi, '$1 personnage');
  t = t.replace(/\bbon\s+perso\b/gi, 'bon personnage');
  t = t.replace(/\bchanger?\s+de\s+perso\b/gi, 'changer de personnage');
  t = t.replace(/\bvends?\s+perso\b/gi, 'vends personnage');

  // Coiffe equipment -> chapeau
  t = t.replace(/\bcoiffes?\b/gi, 'chapeau');

  // Kamas pricing
  t = t.replace(/\b(\d+)\s*m(\d+)\b/gi, '$1.$2M kamas');
  t = t.replace(/(\d+(?:[.,]\d+)?)\s*mk\b/gi, '$1M kamas');
  t = t.replace(/(\d+(?:[.,]\d+)?)\s*kk\b/gi, '$1k kamas');

  // Professions & features -> standard French
  t = t.replace(/\bbrico\b/gi, 'bricoleur');
  t = t.replace(/\bcordo\b/gi, 'cordonnier');
  t = t.replace(/\bjoaillo\b/gi, 'joaillomage');
  t = t.replace(/\balchi\b/gi, 'alchimiste');
  t = t.replace(/\bkoli\b/gi, 'kolizéum');
  t = t.replace(/\bchal\b/gi, 'challenge');
  t = t.replace(/\bchals\b/gi, 'challenges');
  t = t.replace(/\bpopo\s+rappel\b/gi, 'potion de rappel');
  t = t.replace(/\bpopo\s+bonta\b/gi, 'potion de Bonta');
  t = t.replace(/\bpopo\s+brak\b/gi, 'potion de Brâkmar');
  t = t.replace(/\bhs\b/gi, 'havre-sac');

  // Typo: "sa" -> "ça"
  t = t.replace(/\bsa\s+vaut\s+(?:cb|combien)\b/gi, 'combien ça vaut');
  t = t.replace(/\bcombien\s+sa\s+vaut\b/gi, 'combien ça vaut');
  t = t.replace(/\bsa\s+vaut\b/gi, 'ça vaut');
  t = t.replace(/\b(?:sa|ca)\s+te\s+dit\b/gi, 'ça te dit');
  t = t.replace(/\b(?:sa|ca)\s+te\s+tente\b/gi, 'ça te tente');
  t = t.replace(/\b(?:sa|ca)\s+vous\s+dit\b/gi, 'ça vous dit');
  t = t.replace(/\b(?:sa|ca)\s+vous\s+tente\b/gi, 'ça vous tente');
  t = t.replace(/\b(?:sa|ca)\s+marche\b/gi, 'ça marche');
  t = t.replace(/\b(?:sa|ca)\s+roule\b/gi, 'ça roule');
  t = t.replace(/\bcb\b/gi, 'combien');

  // Slang & Phonetics: "cho" -> "chaud", "ki e" -> "qui est"
  t = t.replace(/\b(?:ki|qui)\s+(?:e|est)\s+cho\b/gi, 'qui est chaud');
  t = t.replace(/\b(?:t|t'es|tu\s+es)\s+cho\b/gi, 'tu es chaud');
  t = t.replace(/\b(?:chui|chuis|jsuis|jss|je\s+suis)\s+cho\b/gi, 'je suis chaud');

  // Combat range: CAC (corps-à-corps) & PO (portée)
  t = t.replace(/\b(?:attention|gaffe)\s+au\s+cac\b/gi, 'attention au corps-à-corps');
  t = t.replace(/\breste(?:\s+pas|\s+jamais)?\s+au\s+cac\s+(?:de|du|des)?/gi, 'reste à distance de ');
  t = t.replace(/\bau\s+cac\b/gi, 'au corps-à-corps');
  t = t.replace(/\b(arme|taper|frappe|zone|rester?|reste|t'es|tu\s+es|mon|ton|son)\s+cac\b/gi, '$1 corps-à-corps');
  t = t.replace(/\bcac\b/gi, 'corps-à-corps');
  t = t.replace(/\bldv\b/gi, 'ligne de vue');
  t = t.replace(/\b(?:j'ai\s+pas|jai\s+pas|pas)\s+(?:assez\s+de\s+|la\s+|de\s+)?po\b/gi, 'pas assez de portée');
  t = t.replace(/\bmanque\s+de\s+po\b/gi, 'manque de portée');
  t = t.replace(/\bhors\s+de\s+po\b/gi, 'hors de portée');
  t = t.replace(/\bret\s+pm\b/gi, 'retrait PM');
  t = t.replace(/\bral\s+pm\b/gi, 'retrait PM');
  t = t.replace(/\bret\s+pa\b/gi, 'retrait PA');
  t = t.replace(/\bral\s+pa\b/gi, 'retrait PA');

  // Gaming combat actions & spells
  t = t.replace(/\b(?:se\s+faire\s+|s'est\s+fait\s+|je\s+me\s+suis\s+fait\s+)?os\s+(?:le|un|ce)\s+(?:mob|monstre|boss|adds?)\b/gi, 'one-shot le monstre');
  t = t.replace(/\bos\s+(?:les|des|ces)\s+(?:mobs|monstres|adds?)\b/gi, 'one-shot les monstres');
  t = t.replace(/\bse\s+faire\s+os\b/gi, 'se faire one-shot');
  t = t.replace(/\blib[eé]\s+(?:le|un|ce)\s+mob\b/gi, 'lance Libération sur le monstre');
  t = t.replace(/\bcoop\s+(?:le|un|ce)\s+mob\b/gi, 'lance Coopération sur le monstre');
  t = t.replace(/\bcorrup\s+(?:le|ce)\s+boss\b/gi, 'lance Corruption sur le boss');
  t = t.replace(/\bclean\s+les\s+adds\b/gi, 'nettoie les monstres secondaires');
  t = t.replace(/\btue\s+les\s+adds\b/gi, 'tue les monstres secondaires');
  t = t.replace(/\bclean\s+les\s+mobs\b/gi, 'nettoie les monstres');

  // Gaming Verbs: "taper" before bosses, mobs, dungeons -> "combattre" / "faire" (never "type" or "hit")
  t = t.replace(/\bqui\s+pour\s+taper\s+(?:un\s+|le\s+)?gourlo[t]?\b/gi, 'qui veut faire Gourlo le Terrible');
  t = t.replace(/\bqui\s+pour\s+taper\s+(?:un\s+|le\s+)?rm\b/gi, 'qui veut faire un Royalmouth');
  t = t.replace(/\bqui\s+pour\s+taper\s+(?:un\s+|le\s+)?dc\b/gi, 'qui veut faire un Dragon Cochon');
  t = t.replace(/\bqui\s+pour\s+taper\s+(?:un\s+|le\s+)?br\b/gi, 'qui veut faire un Bouftou Royal');
  t = t.replace(/\bqui\s+pour\s+taper\s+(?:un\s+|le\s+)?cm\b/gi, 'qui veut faire un Chêne Mou');
  t = t.replace(/\b(?:on\s+va\s+)?taper\s+(?:des\s+|les\s+)?mobs?\s+ravageurs?\b/gi, 'combattre les Ravageurs');
  t = t.replace(/\btaper\s+(?:des\s+|les\s+)?ravageurs?\b/gi, 'combattre les Ravageurs');
  t = t.replace(/\b(?:on\s+va\s+)?taper\s+(?:des\s+|les\s+)?mobs?\b/gi, 'combattre les monstres');
  t = t.replace(/\btaper\s+(?:un\s+|le\s+)?gourlo[t]?\b/gi, 'combattre Gourlo');
  t = t.replace(/\btaper\s+(?:un\s+|le\s+)?rm\b/gi, 'combattre un Royalmouth');
  t = t.replace(/\btaper\s+(?:un\s+|le\s+)?dc\b/gi, 'combattre un Dragon Cochon');
  t = t.replace(/\btaper\s+(?:un\s+|le\s+)?br\b/gi, 'combattre un Bouftou Royal');
  t = t.replace(/\btaper\s+(?:un\s+|le\s+)?cm\b/gi, 'combattre un Chêne Mou');
  t = t.replace(/\btaper\s+un\s+(boss|donjon|dj)\b/gi, 'faire un $1');
  t = t.replace(/\btaper\s+le\s+(boss|donjon|dj)\b/gi, 'faire le $1');
  t = t.replace(/\bon\s+go\s+taper\s+/gi, 'on va combattre ');
  t = t.replace(/\bgo\s+taper\s+/gi, 'allons combattre ');
  t = t.replace(/\bon\s+go\s+(?:faire\s+)?/gi, 'on va faire ');

  // RDV context: meet / rendezvous vs Reine des Voleurs
  t = t.replace(/\brdv\s+(?:au\s+|à\s+|a\s+|en\s+|devant\s+|sur\s+)?(zaap\s+village|zaap\s+bonta|zaap\s+brak|zaap\s+astrub|zaap|pos|\[)/gi, 'rendez-vous au $1');
  t = t.replace(/\brdv\s+zaap\b/gi, 'rendez-vous au zaap');
  t = t.replace(/\brdv\s+devant\s+le\s+dj\b/gi, 'rendez-vous devant le donjon');
  t = t.replace(/\b(?:dj|donjon)\s+rdv\b/gi, 'donjon Reine des Voleurs');
  t = t.replace(/\b(?:clé|cle|clés|cles)\s+rdv\b/gi, 'clé de la Reine des Voleurs');
  t = t.replace(/\bpassage\s+rdv\b/gi, 'passage de la Reine des Voleurs');
  t = t.replace(/\bduo\s+rdv\b/gi, 'succès duo Reine des Voleurs');

  // Boss & Dungeon recruit shortcuts
  t = t.replace(/\bqui\s+pour\s+(un\s+|le\s+)?gourlo[t]?\b/gi, 'qui veut faire Gourlo le Terrible');
  t = t.replace(/\bqui\s+pour\s+(un\s+|le\s+)?dc\b/gi, 'qui veut faire un Dragon Cochon');
  t = t.replace(/\bqui\s+pour\s+(un\s+|le\s+)?rm\b/gi, 'qui veut faire un Royalmouth');
  t = t.replace(/\bqui\s+pour\s+(un\s+|le\s+)?br\b/gi, 'qui veut faire un Bouftou Royal');
  t = t.replace(/\bqui\s+pour\s+(un\s+|le\s+)?cm\b/gi, 'qui veut faire un Chêne Mou');
  t = t.replace(/\bqui\s+pour\s+(un\s+|le\s+)?rn\b/gi, 'qui veut faire un Rat Noir');
  t = t.replace(/\bqui\s+pour\s+(un\s+|le\s+)?rb\b/gi, 'qui veut faire un Rat Blanc');
  t = t.replace(/\bqui\s+pour\s+(le\s+|un\s+)?nidas\b/gi, 'qui veut faire le Roi Nidas');
  t = t.replace(/\bqui\s+pour\s+(la\s+)?rdv\b/gi, 'qui veut faire la Reine des Voleurs');
  t = t.replace(/\bqui\s+pour\s+(le\s+)?vortex\b/gi, 'qui veut faire le Vortex');
  t = t.replace(/\bqui\s+pour\s+(le\s+)?chaloeil\b/gi, 'qui veut faire le Chaloeil');
  t = t.replace(/\bqui\s+pour\s+ily(?:zaelle)?\b/gi, 'qui veut faire Ilyzaelle');
  t = t.replace(/\bqui\s+pour\s+danti(?:n[eé]a)?\b/gi, 'qui veut faire Dantinéa');
  t = t.replace(/\bqui\s+pour\s+dj\s+glours\b/gi, 'qui veut faire le donjon Glourséleste');
  t = t.replace(/\bqui\s+pour\s+fri\s*3\b/gi, 'qui veut faire Frigost 3');
  t = t.replace(/\bqui\s+pour\s+fri\s*2\b/gi, 'qui veut faire Frigost 2');
  t = t.replace(/\bqui\s+pour\s+fri\s*1\b/gi, 'qui veut faire Frigost 1');

  // Dungeon Keys shortcuts
  t = t.replace(/\bcl[eé]s?\s+br\b/gi, 'clé du Bouftou Royal');
  t = t.replace(/\bcl[eé]s?\s+rm\b/gi, 'clé du Royalmouth');
  t = t.replace(/\bcl[eé]s?\s+dc\b/gi, 'clé du Dragon Cochon');
  t = t.replace(/\bcl[eé]s?\s+cm\b/gi, 'clé du Chêne Mou');
  t = t.replace(/\bcl[eé]s?\s+rn\b/gi, 'clé du Rat Noir');
  t = t.replace(/\bcl[eé]s?\s+rb\b/gi, 'clé du Rat Blanc');
  t = t.replace(/\bcl[eé]s?\s+glours\b/gi, 'clé du Glourséleste');
  t = t.replace(/\bcl[eé]s?\s+korri\b/gi, 'clé du Korriandre');
  t = t.replace(/\bcl[eé]s?\s+fuji\b/gi, 'clé du Fuji Givrefoux');
  t = t.replace(/\bcl[eé]s?\s+nidas\b/gi, 'clé du Roi Nidas');
  t = t.replace(/\btrousseau(?:\s+de\s+cl[eé]s?)?\b/gi, 'trousseau de clefs');

  // Dungeon carry shortcuts
  t = t.replace(/\bpassage\s+cm\b/gi, 'passage du Chêne Mou');
  t = t.replace(/\bpassage\s+rm\b/gi, 'passage du Royalmouth');
  t = t.replace(/\bpassage\s+dc\b/gi, 'passage du Dragon Cochon');
  t = t.replace(/\bpassage\s+br\b/gi, 'passage du Bouftou Royal');

  // Common Dofus dungeons shortcuts
  t = t.replace(/\bdj\s+glours\b/gi, 'donjon Glourséleste');
  t = t.replace(/\bdj\s+bouf\b/gi, 'donjon des Bouftous');
  t = t.replace(/\bdj\s+blop\b/gi, 'donjon des Blops');
  t = t.replace(/\bdj\s+meulou\b/gi, 'donjon du Meulou');
  t = t.replace(/\bdj\s+bworker\b/gi, 'donjon du Bworker');
  t = t.replace(/\bdj\s+kimbo\b/gi, 'donjon du Kimbo');
  t = t.replace(/\bduo\s+korri\b/gi, 'succès duo Korriandre');

  // Travel & Zaap
  t = t.replace(/\btp\s+dj\b/gi, 'téléporte au donjon');
  t = t.replace(/\btp\s+moi\b/gi, 'téléporte-moi');
  t = t.replace(/\bgo\s+zaap\b/gi, 'allons au zaap');
  t = t.replace(/\bsave\s+zaap\b/gi, 'sauvegarde au zaap');

  // Player invites & party
  t = t.replace(/\b(?:envoie\s+groupe|inv\s+groupe|inv\s+grp)\b/gi, 'invite dans le groupe');
  t = t.replace(/\b(?:inv|invi)\s+stp\b/gi, "invite s'il te plaît");

  // Common French gamer slang & typos
  t = t.replace(/\b(?:pck|parce\s+ke)\b/gi, 'parce que');
  t = t.replace(/\b(?:farm\s+xp|pex|pexe)\b/gi, "gagner de l'expérience");
  t = t.replace(/\b(?:trkl|tranquille)\s+(?:ça|sa)\s+passe\b/gi, 'tranquille on gère');
  t = t.replace(/\btrkl\b/gi, 'tranquille');
  t = t.replace(/\bgg\s+all\b/gi, 'bien joué à tous');
  t = t.replace(/\ba\+\s+bon\s+jeu\b/gi, 'à plus, bon jeu');

  // Trade & Commerce
  t = t.replace(/\b(?:vend|vends)\s+dofus\b/gi, 'je vends Dofus');
  t = t.replace(/\b(?:achete|achète)\s+offres\s+en\s+or\b/gi, "j'achète les offres en or");
  t = t.replace(/\bno\s+arnaque\b/gi, "pas d'arnaque");
  t = t.replace(/\bno\s+noob\b/gi, 'pas de débutant');

  // Technical disconnection & crash expressions
  t = t.replace(/\bj'ai\s+crash\b/gi, 'mon jeu a planté');
  t = t.replace(/\bjai\s+crash\b/gi, 'mon jeu a planté');
  t = t.replace(/\bj'ai\s+d[eé]co\b/gi, "j'ai déconnecté");
  t = t.replace(/\bjai\s+d[eé]co\b/gi, "j'ai déconnecté");
  t = t.replace(/\bje\s+reco\b/gi, 'je me reconnecte');
  t = t.replace(/\breco\s+apr[eè]s\s+le\s+reboot\b/gi, 'reconnexion après le redémarrage');

  // Forgemagie & Gear
  t = t.replace(/\bvoile\s+dencre\b/gi, "Voile d'encre");
  t = t.replace(/\bover\s+vita\b/gi, 'over vitalité');
  t = t.replace(/\bfm\b/gi, 'forgemagie');

  return t;
}
