import { DofusEntry } from '../types/dofus';
import {
  DOFUS_DIMENSIONS_AND_ZONES,
  DOFUS_CLASSES_FR_EN,
  DOFUS_ARCHIMONSTERS_AND_WANTED,
  DOFUS_MONSTER_FAMILIES_ALL_LANGS
} from './dofusExpandedData';

/**
 * Comprehensive database of Dofus Main Quests, Secondary Quests, Primordial & Secondary Dofus,
 * Bounties (Avis de recherche), Archmonster Hunting, Portals, and Treasure Hunts.
 */
export const DOFUS_QUESTS_AND_BOUNTIES_ENTRIES: DofusEntry[] = [
  // ============================================================================
  // 1. BOUNTIES (AVIS DE RECHERCHE), ARCHIMONSTRES, CAPTURES & CHASSES
  // ============================================================================
  {
    fr: 'avis de recherche',
    en: 'bounty',
    aliases_fr: ['avis', 'mob avis', 'recherché', 'monstre recherché', 'les avis'],
    category: 'bounties_and_hunting',
    note: 'Wanted notice / Bounty monster. Ex: "recrute pour avis" -> "LF group for bounty"',
    context_sensitive: false
  },
  {
    fr: 'chasse aux avis',
    en: 'bounty hunting',
    aliases_fr: ['chasse avis', 'farme avis', 'tour des avis', 'chercher avis'],
    category: 'bounties_and_hunting',
    note: 'Searching maps for wanted monsters (bounties)',
    context_sensitive: false
  },
  {
    fr: 'groupe avis',
    en: 'bounty group',
    aliases_fr: ['grp avis', 'team avis', 'dispo avis', 'recrute avis'],
    category: 'bounties_and_hunting',
    note: 'Party formed to defeat and turn in a bounty monster',
    context_sensitive: false
  },
  {
    fr: 'livrer l\'avis',
    en: 'turn in the bounty',
    aliases_fr: ['rendre l\'avis', 'prison avis', 'milice avis'],
    category: 'bounties_and_hunting',
    note: 'Delivering the captured bounty follower to the militia prison for kamas/doploons',
    context_sensitive: false
  },
  {
    fr: 'doplon',
    en: 'doploon',
    aliases_fr: ['doplons', 'échange doplons', 'parchemin doplon'],
    category: 'bounties_and_hunting',
    note: 'Token currency rewarded for defeating Bounties (Avis de recherche)',
    context_sensitive: false
  },
  {
    fr: 'archimonstre',
    en: 'archmonster',
    aliases_fr: ['archi', 'archi-monstre', 'archis', 'mob archi'],
    category: 'bounties_and_hunting',
    note: 'Rare miniboss monster required for the Eternal Harvest (Ochre Dofus)',
    context_sensitive: false
  },
  {
    fr: 'pierre d\'âme',
    en: 'soul stone',
    aliases_fr: ['pda', 'pierre d\'ame', 'pierre ame', 'gigantesque pierre d\'âme'],
    category: 'bounties_and_hunting',
    note: 'Consumable stone equipped to capture monster or boss souls',
    context_sensitive: false
  },
  {
    fr: 'pierre d\'âme pleine',
    en: 'full soul stone',
    aliases_fr: ['pda pleine', 'âme capturée', 'ame boss'],
    category: 'bounties_and_hunting',
    note: 'Soul stone containing captured monsters (used in Arena or Eternal Harvest)',
    context_sensitive: false
  },
  {
    fr: 'arène',
    en: 'arena',
    aliases_fr: ['arene', 'arène bonta', 'arène brakmar', 'taper pda'],
    category: 'bounties_and_hunting',
    note: 'Bonta/Brakmar/Astrub arena where soul stones can be released and fought',
    context_sensitive: false
  },
  {
    fr: 'butin 4',
    en: 'B4 loot',
    es: 'B4 (botín 4)',
    pt: 'B4 (espólio 4)',
    aliases_fr: ['b4', 'pda b4'],
    category: 'bounties_and_hunting',
    note: '4-player loot stone / dungeon run (B4)',
    context_sensitive: false
  },
  {
    fr: 'butin 8',
    en: 'B8',
    es: 'B8',
    pt: 'B8',
    aliases_fr: ['b8', 'pda b8'],
    category: 'bounties_and_hunting',
    note: '8-player loot stone / full 8-man group (B8)',
    context_sensitive: false
  },
  {
    fr: 'sort de capture',
    en: 'Soul Capture spell',
    aliases_fr: ['capture d\'âme', 'capturer', 'sort capture'],
    category: 'bounties_and_hunting',
    note: 'Spell obtained at the end of Bulbig Broozer dungeon to capture souls',
    context_sensitive: false
  },
  {
    fr: 'apprivoisement de monture',
    en: 'Mount Taming spell',
    aliases_fr: ['filet de capture', 'capturer dd', 'capturer muldo', 'capturer volkorne'],
    category: 'bounties_and_hunting',
    note: 'Spell and net used to capture wild Dragoturkeys, Seemyools, or RhETtles',
    context_sensitive: false
  },
  {
    fr: 'metamob',
    en: 'Metamob',
    aliases_fr: ['profil metamob', 'lien metamob', 'échange metamob', 'maj metamob'],
    category: 'bounties_and_hunting',
    note: 'Community platform used to track and trade archmonsters for the Ochre quest',
    context_sensitive: false
  },
  {
    fr: 'doublon archi',
    en: 'duplicate archmonster',
    aliases_fr: ['doublon', 'archi en double', 'échange archi', 'trade archi'],
    category: 'bounties_and_hunting',
    note: 'Extra archmonster soul stone available for 1:1 trading',
    context_sensitive: false
  },
  {
    fr: 'pack ocre',
    en: 'full Ochre pack',
    aliases_fr: ['pack moisson', 'pack complet ocre', 'pack 286 archis'],
    category: 'bounties_and_hunting',
    note: 'Complete set of all 286 archmonster souls for Eternal Harvest',
    context_sensitive: false
  },
  {
    fr: 'truffe divine',
    en: 'Divine Truffle',
    aliases_fr: ['truffes divines', 'kralamoure divin'],
    category: 'bounties_and_hunting',
    note: 'Token used to purchase Archmonster boxes after Eternal Harvest rework',
    context_sensitive: false
  },
  {
    fr: 'boîte à fragments',
    en: 'archmonster fragment box',
    aliases_fr: ['fragments d\'archi', 'fragment anomalie'],
    category: 'bounties_and_hunting',
    note: 'Container granting archmonster fragments',
    context_sensitive: false
  },
  {
    fr: 'chasse au trésor',
    en: 'treasure hunt',
    aliases_fr: ['cat', 'chasse aux trésors', 'indice chasse', 'malle aux trésors'],
    category: 'bounties_and_hunting',
    note: 'Solo activity in the Chesthaven for Roses of the Sands and XP',
    context_sensitive: false
  },
  {
    fr: 'chasse légendaire',
    en: 'legendary treasure hunt',
    aliases_fr: ['carte légendaire', 'coffre légendaire', 'fragment de carte'],
    category: 'bounties_and_hunting',
    note: 'Treasure hunt built from map fragments to fight a bounty chest',
    context_sensitive: false
  },
  {
    fr: 'phare',
    en: 'beacon',
    aliases_fr: ['jalon', 'indice', 'loupe', 'forer'],
    category: 'bounties_and_hunting',
    note: 'Checkpoints and clue markers used during a Treasure Hunt',
    context_sensitive: false
  },
  {
    fr: 'rose des sables',
    en: 'Rose of the Sands',
    aliases_fr: ['rds', 'roses des sables'],
    category: 'bounties_and_hunting',
    note: 'Currency earned in treasure hunts (used for Tourmaline and Crimson Dofus)',
    context_sensitive: false
  },
  {
    fr: 'tourmaline',
    en: 'Tourmaline',
    aliases_fr: ['tourmalines'],
    category: 'bounties_and_hunting',
    note: 'Resource purchased with Roses of the Sands for endgame crafts and quests',
    context_sensitive: false
  },
  {
    fr: 'position portail',
    en: 'portal pos',
    aliases_fr: ['pos portail', 'pos enu', 'pos sram', 'pos xel', 'pos eca', 'portail dim', 'chercher portail'],
    category: 'bounties_and_hunting',
    note: 'Map coordinates of a Divine Dimension portal (Enurado, Srambad, Xelorium, Ecaflipus)',
    context_sensitive: false
  },
  {
    fr: 'modificateur de dimension',
    en: 'dimension modifier',
    aliases_fr: ['modi', 'modificateur', 'modif dim'],
    category: 'bounties_and_hunting',
    note: 'Special combat rule active inside a Divine Dimension',
    context_sensitive: false
  },
  {
    fr: 'anomalie temporelle',
    en: 'temporal anomaly',
    aliases_fr: ['anomalie', 'zaap anomalie', 'bonus zone 120%'],
    category: 'bounties_and_hunting',
    note: 'Zone with boosted XP/drop bonus or Chrono-Anomaly boss fight',
    context_sensitive: false
  },
  {
    fr: 'combat à vagues',
    en: 'wave fight',
    aliases_fr: ['vagues', '5 vagues', 'dj vagues'],
    category: 'bounties_and_hunting',
    note: 'Fight where new monster groups spawn every few turns',
    context_sensitive: false
  },

  // Specific Iconic Bounty Monsters (Avis de Recherche)
  {
    fr: 'Maxi-Malle',
    en: 'Beeteloot',
    aliases_fr: ['maxi malle', 'maximalle', 'avis maxi malle'],
    category: 'bounties_and_hunting',
    note: 'Enutrosor (Enurado) Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Aigripoil',
    en: 'Sourfax',
    aliases_fr: ['avis aigripoil', 'archi aigripoil'],
    category: 'bounties_and_hunting',
    note: 'Enutrosor (Enurado) Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Fouduglen l\'Écureuil',
    en: 'Akornaddikt the Squirrel',
    aliases_fr: ['fouduglen', 'avis fouduglen'],
    category: 'bounties_and_hunting',
    note: 'Astrub Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Brumen Tinctorias',
    en: 'Brumen Tinctorias',
    aliases_fr: ['brumen', 'avis brumen'],
    category: 'bounties_and_hunting',
    note: 'Sidimote Moors Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Padgref Demoël',
    en: 'Nomarow Transplent',
    aliases_fr: ['padgref', 'avis padgref'],
    category: 'bounties_and_hunting',
    note: 'Sakai / Frigost Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Frakacia Leukocytine',
    en: 'Stellia Blutzell',
    aliases_fr: ['frakacia', 'avis frakacia'],
    category: 'bounties_and_hunting',
    note: 'Astrub / Amakna Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Ogivol Scalarcin',
    en: 'Ogivol Scalarcin',
    aliases_fr: ['ogivol', 'avis ogivol'],
    category: 'bounties_and_hunting',
    note: 'Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Zatoïshwan',
    en: 'Zatoishwan',
    aliases_fr: ['zatoishwan', 'zato', 'avis zato'],
    category: 'bounties_and_hunting',
    note: 'Pandala Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Musha l\'Oni',
    en: 'Musha the Oni',
    aliases_fr: ['musha', 'avis musha'],
    category: 'bounties_and_hunting',
    note: 'Pandala Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Qil Bil',
    en: 'Qil Bil',
    aliases_fr: ['qilbil', 'avis qil bil'],
    category: 'bounties_and_hunting',
    note: 'Wabbit Island Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Viti Glourson',
    en: 'Viti Glourson',
    aliases_fr: ['viti', 'avis viti'],
    category: 'bounties_and_hunting',
    note: 'Frigost Bearbarian Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Fantômayte',
    en: 'Fantomayte',
    aliases_fr: ['fantomayte', 'avis fantomayte'],
    category: 'bounties_and_hunting',
    note: 'Frigost Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Docteur Eggob',
    en: 'Doctor Eggob',
    aliases_fr: ['eggob', 'dr eggob', 'avis eggob'],
    category: 'bounties_and_hunting',
    note: 'Frigost III Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Mécano du Krosmoz',
    en: 'Krosmoz Mechanic',
    aliases_fr: ['mecano', 'avis dimension'],
    category: 'bounties_and_hunting',
    note: 'Divine Dimension Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Carlita de la Vega',
    en: 'Carlita de la Vega',
    aliases_fr: ['carlita', 'avis sram'],
    category: 'bounties_and_hunting',
    note: 'Srambad Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'L\'Éternel',
    en: 'The Eternal',
    aliases_fr: ['eternel', 'avis xel', 'avis xélorium'],
    category: 'bounties_and_hunting',
    note: 'Xelorium Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Truffo le Marol',
    en: 'Truffo',
    aliases_fr: ['truffo', 'avis ecaflipus'],
    category: 'bounties_and_hunting',
    note: 'Ecaflipus Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Simbadas',
    en: 'Simbadas',
    aliases_fr: ['avis saharach'],
    category: 'bounties_and_hunting',
    note: 'Saharach Wanted / Bounty monster',
    context_sensitive: false
  },
  {
    fr: 'Predagob',
    en: 'Predagob',
    aliases_fr: ['avis nimotopia'],
    category: 'bounties_and_hunting',
    note: 'Nimotopia Wanted / Bounty monster',
    context_sensitive: false
  },

  // ============================================================================
  // 2. QUÊTES DES 6 DOFUS PRIMORDIAUX (PRINCIPALES)
  // ============================================================================
  {
    fr: 'L\'Éternelle Moisson',
    en: 'Eternal Harvest',
    aliases_fr: ['éternelle moisson', 'eternelle moisson', 'moisson', 'quête ocre', 'etape ocre'],
    category: 'quests',
    note: 'Main questline by Otomaï to obtain the Ochre Dofus (35 steps)',
    context_sensitive: false
  },
  {
    fr: 'Dofus Ocre',
    en: 'Ochre Dofus',
    aliases_fr: ['ocre', 'le dofus ocre'],
    category: 'quests',
    note: 'Primordial Dofus granting +1 AP',
    context_sensitive: false
  },
  {
    fr: 'Dofus Émeraude',
    en: 'Emerald Dofus',
    aliases_fr: ['émeraude', 'emeraude', 'quête émeraude', 'dark vlad'],
    category: 'quests',
    note: 'Primordial Dofus questline involving Mériana, Dark Vlad, and Cania bandits',
    context_sensitive: false
  },
  {
    fr: 'Qui sème le vent récolte l\'Artempête',
    en: 'Reap the Whirlwind',
    aliases_fr: ['artempête', 'artempete', 'boussole de mériana'],
    category: 'quests',
    note: 'Main Emerald Dofus questline step',
    context_sensitive: false
  },
  {
    fr: 'Bandits de Cania',
    en: 'Cania Bandits',
    aliases_fr: ['bandits cania', 'écailles de dragon', 'edass', 'nomekop', 'erecram', '3 bandits'],
    category: 'quests',
    note: 'Three bounty bosses required for the Emerald Dofus quest',
    context_sensitive: false
  },
  {
    fr: 'Dofus Pourpre',
    en: 'Crimson Dofus',
    aliases_fr: ['pourpre', 'quête pourpre', 'totankama', 'labyrinthe du minotoror'],
    category: 'quests',
    note: 'Primordial Dofus granting +80% Power (Totankama\'s treasure & Minotot)',
    context_sensitive: false
  },
  {
    fr: 'Le trésor de Totankama',
    en: 'Totankama\'s Treasure',
    aliases_fr: ['tablettes de totankama', 'momie nova'],
    category: 'quests',
    note: 'Culminating quest for the Crimson Dofus',
    context_sensitive: false
  },
  {
    fr: 'Dofus Turquoise',
    en: 'Turquoise Dofus',
    aliases_fr: ['turquoise', 'tutu', 'quête tutu', 'bolgrot', 'aguabrial'],
    category: 'quests',
    note: 'Primordial Dofus granting +10% Critical Hits (tactical boss fights)',
    context_sensitive: false
  },
  {
    fr: 'Fureur de Bolgrot',
    en: 'Bolgrot\'s Fury',
    aliases_fr: ['combat bolgrot', 'esprit de bolgrot', 'combat tactique bolgrot'],
    category: 'quests',
    note: 'Final tactical puzzle fight of the Turquoise Dofus questline',
    context_sensitive: false
  },
  {
    fr: 'Dofus Ivoire',
    en: 'Ivory Dofus',
    aliases_fr: ['ivoire', 'quête ivoire', 'alignement 100', 'dardan'],
    category: 'quests',
    note: 'Primordial Dofus requiring level 100 Bonta or Brakmar alignment quests',
    context_sensitive: false
  },
  {
    fr: 'Dofus Ébène',
    en: 'Ebony Dofus',
    aliases_fr: ['ébène', 'ebene', 'quête ébène', 'grugalorasalar'],
    category: 'quests',
    note: 'Primordial Dofus involving the black dragon Grugalorasalar',
    context_sensitive: false
  },
  {
    fr: 'Six sur Six',
    en: 'Six out of Six',
    aliases_fr: ['6/6', 'réunification', 'reunification des dofus', 'quête 6 sur 6'],
    category: 'quests',
    note: 'Culminating main storyline quest uniting all 6 Primordial Dofus',
    context_sensitive: false
  },

  // ============================================================================
  // 3. QUÊTES DES DOFUS SECONDAIRES & RÉGIONAUX
  // ============================================================================
  {
    fr: 'Dofus Vulbis',
    en: 'Vulbis Dofus',
    aliases_fr: ['vulbis', 'quête vulbis', 'parangon', 'parangon de puissance', 'rêve de crocabulia'],
    category: 'quests',
    note: 'Legendary Dofus granting +1 MP (Dreggon Peninsula & Paragon drop)',
    context_sensitive: false
  },
  {
    fr: 'Parangon de puissance',
    en: 'Paragon of Power',
    aliases_fr: ['drop parangon', 'farme parangon'],
    category: 'quests',
    note: 'Rare quest drop from level 200 dungeon bosses required for Vulbis Dofus',
    context_sensitive: false
  },
  {
    fr: 'Dofus des Glaces',
    en: 'Ice Dofus',
    aliases_fr: ['ddg', 'quête ddg', 'dofus glace', 'les oeufs de la discorde'],
    category: 'quests',
    note: 'Major Frigost I, II & III questline reward (+25 all elemental damage)',
    context_sensitive: false
  },
  {
    fr: 'Dofus Abyssal',
    en: 'Abyssal Dofus',
    aliases_fr: ['abyssal', 'quête abyssal', 'sufokia abysses'],
    category: 'quests',
    note: 'Sufokian Abyss questline Dofus granting +1 MP or +1 AP each turn',
    context_sensitive: false
  },
  {
    fr: 'Dofus Nébuleux',
    en: 'Cloudy Dofus',
    aliases_fr: ['nébuleux', 'nebuleux', 'quête nébuleux', 'succès dimensions'],
    category: 'quests',
    note: 'Divine Dimensions questline Dofus (Enurado, Srambad, Xelorium, Ecaflipus)',
    context_sensitive: false
  },
  {
    fr: 'Dofus des Veilleurs',
    en: 'Watchers Dofus',
    aliases_fr: ['veilleurs', 'dofus veilleurs', 'quête veilleurs'],
    category: 'quests',
    note: 'Dimension questline Dofus healing allies anchored in line at end of turn',
    context_sensitive: false
  },
  {
    fr: 'Dofus Argenté',
    en: 'Silver Dofus',
    aliases_fr: ['argenté', 'argente', 'dofus argenté scintillant', 'astrub dofus'],
    category: 'quests',
    note: 'First Dofus earned by completing Astrub main quests (and Sparkling upgrade in Cania)',
    context_sensitive: false
  },
  {
    fr: 'Dofus Cawotte',
    en: 'Cawwot Dofus',
    aliases_fr: ['cawotte', 'quête cawotte', 'wa wabbit'],
    category: 'quests',
    note: 'Wabbit Island questline Dofus granting +60 Wisdom',
    context_sensitive: false
  },
  {
    fr: 'Dokoko',
    en: 'Dokoko',
    aliases_fr: ['dofus dokoko', 'quête moon'],
    category: 'quests',
    note: 'Moon Island questline Dofus restoring 10% max HP every 3 turns',
    context_sensitive: false
  },
  {
    fr: 'Dolmanax',
    en: 'Dolmanax',
    aliases_fr: ['almanax', 'offrande almanax', 'pages du calendrier', '365 pages'],
    category: 'quests',
    note: 'Dofus obtained after 365 daily Almanax temple offerings',
    context_sensitive: false
  },
  {
    fr: 'Dofus Kaliptus',
    en: 'Kaliptus Dofus',
    aliases_fr: ['kaliptus', 'dofus kaliptus', 'repaire de skonk'],
    category: 'quests',
    note: 'Dofus granting Prospecting, obtained at the end of Skeunk\'s Hideout',
    context_sensitive: false
  },
  {
    fr: 'Domakuro',
    en: 'Domakuro Dofus',
    aliases_fr: ['dofus domakuro', 'pandala dofus'],
    category: 'quests',
    note: 'First Pandala questline Dofus',
    context_sensitive: false
  },
  {
    fr: 'Dorigami',
    en: 'Dorigami',
    aliases_fr: ['dofus dorigami'],
    category: 'quests',
    note: 'Second Pandala questline Dofus granting shield points',
    context_sensitive: false
  },
  {
    fr: 'Dofus Tacheté',
    en: 'Spotted Dofus',
    aliases_fr: ['tacheté', 'tachete', 'quête pandala 3'],
    category: 'quests',
    note: 'Culminating Pandala Dofus uniting Domakuro and Dorigami',
    context_sensitive: false
  },
  {
    fr: 'Dofus Cauchemar',
    en: 'Nightmare Dofus',
    aliases_fr: ['cauchemar', 'quête cauchemar'],
    category: 'quests',
    note: 'Valonia / Nightmare questline Dofus',
    context_sensitive: false
  },
  {
    fr: 'Dofus Forgelave',
    en: 'Lavasmith Dofus',
    aliases_fr: ['forgelave', 'lavasmith', 'quête sidimote'],
    category: 'quests',
    note: 'Sidimote Moors questline Dofus granting pushback resistance',
    context_sensitive: false
  },
  {
    fr: 'Dofus Sylvestre',
    en: 'Sylvan Dofus',
    aliases_fr: ['sylvestre', 'arbre de vie'],
    category: 'quests',
    note: 'Endgame questline Dofus',
    context_sensitive: false
  },

  // ============================================================================
  // 4. SÉRIES DE QUÊTES PRINCIPALES, ALIGNEMENT & ÉTAPES CÉLÈBRES
  // ============================================================================
  {
    fr: 'Tour du Monde',
    en: 'Around the World quest',
    aliases_fr: ['quête tour du monde', 'le tour du monde', 'tdm'],
    category: 'quests',
    note: 'Classic dungeon progression quest series ending at Giant Kralove',
    context_sensitive: false
  },
  {
    fr: 'Quêtes d\'alignement',
    en: 'Alignment quests',
    aliases_fr: ['alignement', 'quête ali', 'ali bonta', 'ali brak', 'ali 100', 'ordre d\'alignement'],
    category: 'quests',
    note: '100-quest series for Bonta or Brakmar (required for Ivory Dofus)',
    context_sensitive: false
  },
  {
    fr: 'dalles',
    en: 'floor tiles / pressure plates',
    aliases_fr: ['dalle', 'poser sur la dalle', 'ouverture dalle', 'cherche monde dalle'],
    category: 'quests',
    note: 'Co-op quest step where multiple players must stand on floor tiles simultaneously',
    context_sensitive: false
  },
  {
    fr: 'ouverture Kralamoure',
    en: 'Giant Kralove opening',
    aliases_fr: ['ouverture krala', 'dalles krala', 'ouvrir krala'],
    category: 'quests',
    note: 'Gathering 48 players on Otomai tiles to open the Giant Kralove dungeon for Ochre/Tour du Monde',
    context_sensitive: false
  },
  {
    fr: 'L\'Éliocalypse',
    en: 'The Eliocalypse',
    aliases_fr: ['éliocalypse', 'eliocalypse', 'quêtes éliocalypse', 'cavaliers de l\'eliocalypse'],
    category: 'quests',
    note: 'Endgame main story arc against the 4 Horsemen of the Eliocalypse (War, Corruption, Misery, Servitude)',
    context_sensitive: false
  },
  {
    fr: 'combat tactique de quête',
    en: 'tactical quest fight',
    aliases_fr: ['combat tactique', 'combat de quête', 'combat solo quête'],
    category: 'quests',
    note: 'Special quest battle with fixed spells or specific mechanics',
    context_sensitive: false
  },
  {
    fr: 'prérequis de quête',
    en: 'quest prerequisite',
    aliases_fr: ['prérequis', 'prerequis', 'bloque quête'],
    category: 'quests',
    note: 'Prior quests, alignment level, or job level needed to start a quest',
    context_sensitive: false
  },
  {
    fr: 'étape de quête',
    en: 'quest step',
    aliases_fr: ['étape', 'etape quete', 'bloqué étape'],
    category: 'quests',
    note: 'Specific objective within a multi-step quest',
    context_sensitive: false
  },
  {
    fr: 'escorte PNJ',
    en: 'NPC escort quest',
    aliases_fr: ['protéger pnj', 'suivre pnj', 'pnj suiveur'],
    category: 'quests',
    note: 'Quest requiring keeping an NPC alive in combat or across maps',
    context_sensitive: false
  },
  {
    fr: 'Un citoyen modèle',
    en: 'A Model Citizen',
    aliases_fr: ['citoyen modèle', 'succès astrub', 'quêtes astrub'],
    category: 'quests',
    note: 'Main Astrub quest meta-achievement awarding the Silver Dofus',
    context_sensitive: false
  },
  {
    fr: 'Le Réveil de Pandala',
    en: 'Pandala Awakens',
    aliases_fr: ['réveil de pandala', 'quetes pandala', 'pandala 1', 'pandala 2', 'pandala 3'],
    category: 'quests',
    note: 'Main Pandala storyline arc',
    context_sensitive: false
  },
  {
    fr: 'L\'Étoile des Neiges',
    en: 'Snow Star',
    aliases_fr: ['étoile des neiges', 'quetes frigost', 'maire cantile'],
    category: 'quests',
    note: 'Main Frigost storyline quest series',
    context_sensitive: false
  },
  {
    fr: 'Fil d\'Ariane',
    en: 'Ariadne\'s Thread',
    aliases_fr: ['fil d\'ariane', 'quêtes dimensions', 'avant-poste'],
    category: 'quests',
    note: 'Divine Dimensions storyline quests',
    context_sensitive: false
  },
  {
    fr: 'La Sorcière des Marécages',
    en: 'The Swamp Witch',
    aliases_fr: ['sorcière des marécages', 'mériana', 'meriana'],
    category: 'quests',
    note: 'Key main storyline quest with Mériana in the Nauseating Swamps',
    context_sensitive: false
  },
  {
    fr: 'Restaurer la Constitution',
    en: 'Restore Otomai\'s Zoth / Reset quests',
    aliases_fr: ['quêtes otomaï', 'quetes otomai', 'reliques otomaï'],
    category: 'quests',
    note: 'Otomai Island questline through all 5 island dungeons',
    context_sensitive: false
  }
];

/**
 * Generates unified DofusEntry items for all expanded quests, bounties, zones, classes, and bosses
 * so the dictionary browser and translator have full access to them.
 */
export function getAllExpandedDofusEntries(): DofusEntry[] {
  const result: DofusEntry[] = [...DOFUS_QUESTS_AND_BOUNTIES_ENTRIES];

  // Add Zones & Divine Dimensions
  for (const [frZone, enZone] of Object.entries(DOFUS_DIMENSIONS_AND_ZONES)) {
    // Avoid duplicates with accents
    if (!result.some(e => e.fr.toLowerCase() === frZone.toLowerCase())) {
      result.push({
        fr: frZone.charAt(0).toUpperCase() + frZone.slice(1),
        en: enZone,
        aliases_fr: [],
        category: 'zone',
        note: 'Dimension divine / Région du Monde des Douze',
        context_sensitive: false
      });
    }
  }

  // Add Classes & Abbreviations
  for (const [frClass, classInfo] of Object.entries(DOFUS_CLASSES_FR_EN)) {
    if (!result.some(e => e.en.toLowerCase() === classInfo.en.toLowerCase() && e.category === 'builds_and_classes')) {
      result.push({
        fr: frClass.charAt(0).toUpperCase() + frClass.slice(1),
        en: classInfo.en,
        aliases_fr: classInfo.short,
        category: 'builds_and_classes',
        note: `Classe officielle Dofus (${classInfo.en})`,
        context_sensitive: false
      });
    }
  }

  // Add Bosses & Archimonsters
  for (const [frMob, enMob] of Object.entries(DOFUS_ARCHIMONSTERS_AND_WANTED)) {
    if (!result.some(e => e.fr.toLowerCase() === frMob.toLowerCase())) {
      result.push({
        fr: frMob.charAt(0).toUpperCase() + frMob.slice(1),
        en: enMob,
        aliases_fr: [],
        category: 'monster',
        note: 'Boss de donjon / Archi-monstre Dofus',
        context_sensitive: false
      });
    }
  }

  // Add Monster Families (Ravageurs, Gloursons, Mansots, etc.)
  for (const fam of DOFUS_MONSTER_FAMILIES_ALL_LANGS) {
    if (!result.some(e => e.fr.toLowerCase() === fam.fr.toLowerCase() && e.category === 'monster')) {
      result.push({
        fr: fam.fr,
        en: fam.en,
        es: fam.es,
        pt: fam.pt,
        aliases_fr: fam.short,
        category: 'monster',
        note: `Famille de monstres officielle (${fam.en})`,
        context_sensitive: false
      });
    }

    // Add Singular Monster if different
    if (fam.fr_singular && fam.fr_singular.toLowerCase() !== fam.fr.toLowerCase()) {
      if (!result.some(e => e.fr.toLowerCase() === fam.fr_singular!.toLowerCase() && e.category === 'monster')) {
        result.push({
          fr: fam.fr_singular,
          en: fam.en_singular || fam.en,
          es: fam.es_singular || fam.es,
          pt: fam.pt_singular || fam.pt,
          aliases_fr: [fam.fr_singular.toLowerCase(), `un ${fam.fr_singular.toLowerCase()}`],
          category: 'monster',
          note: `Monstre officiel (${fam.en_singular || fam.en})`,
          context_sensitive: false
        });
      }
    }
  }

  return result;
}
