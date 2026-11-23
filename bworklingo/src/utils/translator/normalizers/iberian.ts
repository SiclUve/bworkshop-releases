import { DofusLanguage } from '../../../types/dofus';

/**
 * Normalizes common Spanish (ES) and Portuguese / PT-BR (PT) gaming slang,
 * Dofus community abbreviations, and chat typos strictly within their respective languages.
 */
export function normalizeIberianGamingChat(text: string, lang: DofusLanguage): string {
  if (!text) return '';
  let t = text;

  // Separate numbers stuck to units like "2min", "4cbts"
  t = t.replace(/(\d+)\s*(minutos?|mins?|horas?|turnos?|combates?|cbt)\b/gi, '$1 $2');

  if (lang === 'pt') {
    // Greetings & SMS shortcuts (PT-BR)
    t = t.replace(/\b(?:obg|obgd|obrigadao|vlw|valeu)\b/gi, 'obrigado');
    t = t.replace(/\b(?:pfv|pff|pf|plz|pls)\b/gi, 'por favor');
    t = t.replace(/\btmj\b/gi, 'estamos juntos');
    t = t.replace(/\bblz\b/gi, 'combinado');
    t = t.replace(/\bflw\b/gi, 'até mais');
    t = t.replace(/\b(?:trq|tranqs|suave|de\s+boa)\b/gi, 'tranquilo');
    t = t.replace(/\b(?:td\s+bem|tdb)\b/gi, 'tudo bem');
    t = t.replace(/\btd\s+certo\b/gi, 'tudo certo');
    t = t.replace(/\b(?:vc|c[êe])\b/gi, 'você');
    t = t.replace(/\bvcs\b/gi, 'vocês');
    t = t.replace(/\b(?:tbm|tb)\b/gi, 'também');
    t = t.replace(/\bpq\b/gi, 'porque');
    t = t.replace(/\bqm\b/gi, 'quem');
    t = t.replace(/\balgm\b/gi, 'alguém');
    t = t.replace(/\bngm\b/gi, 'ninguém');
    t = t.replace(/\b(?:kd|cade)\b/gi, 'cadê');
    t = t.replace(/\bagr\b/gi, 'agora');
    t = t.replace(/\bhj\b/gi, 'hoje');
    t = t.replace(/\bamanha\b/gi, 'amanhã');
    t = t.replace(/\b(?:mto|mt)\b/gi, 'muito');
    t = t.replace(/\bmta\b/gi, 'muita');
    t = t.replace(/\baki\b/gi, 'aqui');
    t = t.replace(/\bcmg\b/gi, 'comigo');
    t = t.replace(/\bctg\b/gi, 'contigo');
    t = t.replace(/\bmsm\b/gi, 'mesmo');
    t = t.replace(/\bnda\b/gi, 'nada');
    t = t.replace(/\b(?:nao|nn|n)\s+(?=sei|tenho|da|d[aá]|consigo|posso|quero|vai|tem|foi|ta|t[aá]|preciso)/gi, 'não ');
    t = t.replace(/\bnao\b/gi, 'não');
    t = t.replace(/\bpra\b/gi, 'para');
    t = t.replace(/\bpro\b/gi, 'para o');
    t = t.replace(/\bpros\b/gi, 'para os');
    t = t.replace(/\bpras\b/gi, 'para as');
    t = t.replace(/\bq\s+(?=vc|vcs|isso|ele|ela|nos|n[oó]s|eu|tu|vai|tem|quer|fazer|passa)/gi, 'que ');
    t = t.replace(/\bta\s+(?=bugado|morto|vivo|pronto|salvo|caro|barato|dif[ií]cil|f[aá]cil|on|off|no|na|em)/gi, 'está ');
    t = t.replace(/\bto\s+(?=indo|pronto|aqui|aki|sem|com|no|na|em|fazendo|procurando|vendendo|comprando)/gi, 'estou ');
    t = t.replace(/\b(?:bora\s+la|bora)\b/gi, 'vamos');

    // Frigost & Levels & Kamas
    t = t.replace(/\b(?:lv+l|nv|niv)\b/gi, 'nível');
    t = t.replace(/\b(?:fri\s*3|f3)\b/gi, 'Frigost 3');
    t = t.replace(/\b(?:fri\s*2|f2)\b/gi, 'Frigost 2');
    t = t.replace(/\b(?:fri\s*1|f1)\b/gi, 'Frigost 1');
    t = t.replace(/(\d+(?:[.,]\d+)?)\s*mk\b/gi, '$1M kamas');
    t = t.replace(/(\d+(?:[.,]\d+)?)\s*kk\b/gi, '$1k kamas');
    t = t.replace(/\b(\d+)\s*m(\d+)\b/gi, '$1.$2M kamas');
    t = t.replace(/\bc\/u\b/gi, 'cada um');

    // Dungeons, PvM & Collectors (PT)
    t = t.replace(/\bdgs\b/gi, 'calabouços');
    t = t.replace(/\bdg\b/gi, 'calabouço');
    t = t.replace(/\bcalas\b/gi, 'calabouços');
    t = t.replace(/\bcala\b/gi, 'calabouço');
    t = t.replace(/\bcbt\b/gi, 'combate');
    t = t.replace(/\bpercs\b/gi, 'coletores');
    t = t.replace(/\bperc\b/gi, 'coletor');
    t = t.replace(/\bbichos\b/gi, 'monstros');
    t = t.replace(/\bbicho\b/gi, 'monstro');
    t = t.replace(/\barquis?\b/gi, 'arquimonstro');
    t = t.replace(/\bultima\s+vaga\b/gi, 'última vaga');
    t = t.replace(/\bkoli\b/gi, 'Koliseu');
    t = t.replace(/\btp\s+(?:cala|calabou[cç]o)\b/gi, 'teleporta ao calabouço');
    t = t.replace(/\bsalv[aeo]r?\s+zaap\b/gi, 'salve no zaap');
    t = t.replace(/\bsalv[eo]\s+(?:no\s+)?boss\b/gi, 'salvo no boss');
    t = t.replace(/\bmolho\s+de\s+chaves?\b/gi, 'chaveiro');
    t = t.replace(/\bsue?onhos\b|\bsonhos\b/gi, 'Sonhos Infinitos');

    // Sets & Stats & Combat Mechanics (PT)
    t = t.replace(/\bfull\s+sab\b|\b(?:set|conj(?:unto)?)\s+sab(?:edoria)?\b/gi, 'conjunto de sabedoria');
    t = t.replace(/\bfull\s+pp\b|\b(?:set|conj(?:unto)?)\s+pp\b/gi, 'conjunto de prospecção');
    t = t.replace(/\b(?:set|conj)\s+papatudo\s+real\b/gi, 'conjunto de Papatudo Real');
    t = t.replace(/\b(?:set|conj)\s+papatudo\b/gi, 'conjunto de Papatudo');
    t = t.replace(/\b(?:set|conj)\s+mulobo\b/gi, 'conjunto de Mulobo');
    t = t.replace(/\b(?:set|conj)\s+carvalho(?:\s+mole)?\b/gi, 'conjunto de Carvalho Mole');
    t = t.replace(/\b(?:set|conj)\s+piu\b/gi, 'conjunto de Piu');
    t = t.replace(/\bcac\b/gi, 'combate corpo a corpo');
    t = t.replace(/\bsem\s+ldv\b/gi, 'sem linha de visão');
    t = t.replace(/\bldv\b/gi, 'linha de visão');
    t = t.replace(/\b(?:sem|falta(?:\s+de)?)\s+po\b/gi, 'falta de alcance');
    t = t.replace(/\b(?:ret|ral)\s+pm\b/gi, 'redução de PM');
    t = t.replace(/\b(?:ret|ral)\s+pa\b/gi, 'redução de PA');
    t = t.replace(/\b(?:limpa|limpar)\s+(?:os\s+)?adds?\b/gi, 'limpe os lacaios');
    t = t.replace(/\b(?:mata|matar)\s+(?:os\s+)?adds?\b/gi, 'mate os lacaios');
    t = t.replace(/\bos\s+(?:no|o)\s+(?:mob|monstro)\b/gi, 'derrotar de um golpe o monstro');

    // Invites, Trade & Crash (PT)
    t = t.replace(/\b(?:prc|procuro)\s+grp\b/gi, 'procuro grupo');
    t = t.replace(/\b(?:inv|invi)(?:\s+(?:por\s+favor|pfv))?\b/gi, (m) => (/por\s+favor|pfv/i.test(m) ? 'convida por favor' : 'convida'));
    t = t.replace(/\b(?:chama|manda)\s+(?:no\s+)?pm\b/gi, 'manda mp');
    t = t.replace(/\bwhispa\b/gi, 'manda mp');
    t = t.replace(/\bvdo\b/gi, 'vendo');
    t = t.replace(/\bcpo\b/gi, 'compro');
    t = t.replace(/\b(?:sem\s+choro|preco\s+fixo)\b/gi, 'preço fixo');
    t = t.replace(/\bsem\s+golpistas?\b|\bsem\s+golpe\b/gi, 'sem golpes');
    t = t.replace(/\bfm\b/gi, 'forjamagia');
    t = t.replace(/\brolagem\s+perf(?:eita)?\b/gi, 'rolagem perfeita');
    t = t.replace(/\blevei\s+dc\b|\bcrashei\b|\bmeu\s+jogo\s+(?:travou|fechou)\b/gi, 'meu jogo travou');
  } else if (lang === 'es') {
    // Greetings & SMS shortcuts (ES)
    t = t.replace(/\b(?:wenas|bnas|holi|ola)\b/gi, 'hola');
    t = t.replace(/\b(?:porfa|xfa|xf|pf|pls|plz)\b/gi, 'por favor');
    t = t.replace(/\b(?:grx|grax|grasias|thx)\b/gi, 'gracias');
    t = t.replace(/\bntp\b/gi, 'no te preocupes');
    t = t.replace(/\b(?:tmb|tamb|tmbn)\b/gi, 'también');
    t = t.replace(/\b(?:dnd|dond)\b/gi, 'dónde');
    t = t.replace(/\b(?:xq|xke)\b/gi, 'por qué');
    t = t.replace(/\bpq\b/gi, 'porque');
    t = t.replace(/\b(?:kn|kien|qien)\b/gi, 'quién');
    t = t.replace(/\bmñn\b/gi, 'mañana');
    t = t.replace(/\b(?:bn)\b/gi, 'bien');
    t = t.replace(/\b(?:toy|toi)\b/gi, 'estoy');
    t = t.replace(/\b(?:vms|vams)\b/gi, 'vamos');
    // Spanish "pa" -> "para" ONLY when acting as preposition, NEVER when it means AP ("exo PA", "pozo PA", "+1 PA", "ret PA")
    t = t.replace(/(?<![+\d]\s*)(?<!exo\s)(?<!pozo\s)(?<!ret\s)(?<!ral\s)\bpa\s+(?=hacer|ir|matar|pasar|vender|comprar|mazmorra|mazmo|koli|coliseo|arena|todos|mi|m[ií]|ti|eso|el|la|los|las|un|una|logro|logros|dropear|drop|levelear|subir|capturar|bos|boss)/gi, 'para ');
    t = t.replace(/(?<=\b(?:alguien|qui[eé]n|quien|vamos|grupo|busco|recluto)\s+)pa\b/gi, 'para');
    t = t.replace(/\b(?:q|k|ke)\s+(?=haces|tal|onda|pasa|dices|vale|cuesta|necesitas|quieres|buscas|alguien|nos|se|me|te|es|son|hay|no)/gi, 'que ');
    t = t.replace(/(?<=\b(?:lo|el\s+bicho|el\s+boss|la\s+mazmorra|creo|para|pa)\s+)(?:q|k)\b/gi, 'que');

    // Frigost & Levels & Kamas
    t = t.replace(/\b(?:lv+l|nv|niv)\b/gi, 'nivel');
    t = t.replace(/\b(?:fri\s*3|f3)\b/gi, 'Frigost 3');
    t = t.replace(/\b(?:fri\s*2|f2)\b/gi, 'Frigost 2');
    t = t.replace(/\b(?:fri\s*1|f1)\b/gi, 'Frigost 1');
    t = t.replace(/(\d+(?:[.,]\d+)?)\s*mk\b/gi, '$1M kamas');
    t = t.replace(/(\d+(?:[.,]\d+)?)\s*kk\b/gi, '$1k kamas');
    t = t.replace(/\b(\d+)\s*m(\d+)\b/gi, '$1.$2M kamas');
    t = t.replace(/\bc\/u\b/gi, 'cada uno');

    // Dungeons, PvM & Collectors (ES)
    t = t.replace(/\bmazmos\b/gi, 'mazmorras');
    t = t.replace(/\bmazmo\b/gi, 'mazmorra');
    t = t.replace(/\bdj\b/gi, 'mazmorra');
    t = t.replace(/\brecas\b/gi, 'recaudadores');
    t = t.replace(/\breca\b/gi, 'recaudador');
    t = t.replace(/\bpercos\b/gi, 'recaudadores');
    t = t.replace(/\bperco\b/gi, 'recaudador');
    t = t.replace(/\bbichos\b/gi, 'monstruos');
    t = t.replace(/\bbicho\b/gi, 'monstruo');
    t = t.replace(/\bar[cq]uis?\b/gi, 'archimonstruos');
    t = t.replace(/\bcupos\b/gi, 'plazas');
    t = t.replace(/\bcupo\b/gi, 'plaza');
    t = t.replace(/\b(?:ulti?|ultimo)\b/gi, 'último');
    t = t.replace(/\bcbt\b/gi, 'combate');
    t = t.replace(/\bkoli\b/gi, 'Koliseo');
    t = t.replace(/\btp\s+(?:mazmo|mazmorra)\b/gi, 'teletransporta a la mazmorra');
    t = t.replace(/\b(?:guardo|guarda)\s+zaap\b/gi, 'guarda en el zaap');
    t = t.replace(/\b(?:salvo|guardado)\s+(?:en\s+)?boss\b/gi, 'guardado en boss');
    t = t.replace(/\bllavero\b/gi, 'manojo de llaves');
    t = t.replace(/\bsuenos\b/gi, 'Sueños Infinitos');

    // Sets & Stats & Combat Mechanics (ES)
    t = t.replace(/\bfull\s+sab\b|\bset\s+sab(?:iduria|idur[ií]a)?\b/gi, 'set de sabiduría');
    t = t.replace(/\bfull\s+pp\b|\bset\s+pp\b/gi, 'set de prospección');
    t = t.replace(/\bset\s+jalato\s+real\b/gi, 'set de Jalató Real');
    t = t.replace(/\bset\s+jalato\b/gi, 'set de Jalató');
    t = t.replace(/\bset\s+maxilubo\b/gi, 'set de Maxilubo');
    t = t.replace(/\bset\s+roble(?:\s+blando)?\b/gi, 'set de Roble Blando');
    t = t.replace(/\bset\s+pio\b/gi, 'set de Pío');
    t = t.replace(/\bcac\b|\ba\s+mel[eé]\b/gi, 'cuerpo a cuerpo');
    t = t.replace(/\bsin\s+ldv\b/gi, 'sin línea de visión');
    t = t.replace(/\bldv\b/gi, 'línea de visión');
    t = t.replace(/\b(?:sin|falta(?:\s+de)?)\s+(?:al|po)\b/gi, 'falta de alcance');
    t = t.replace(/\b(?:ret|ral)\s+pm\b/gi, 'reducción de PM');
    t = t.replace(/\b(?:ret|ral)\s+pa\b/gi, 'reducción de PA');
    t = t.replace(/\b(?:limpia|limpiar)\s+(?:los\s+)?adds?\b/gi, 'limpia los esbirros');
    t = t.replace(/\b(?:mata|matar)\s+(?:los\s+)?adds?\b/gi, 'mata los esbirros');
    t = t.replace(/\bos\s+(?:al|el)\s+(?:bicho|mob|monstruo)\b/gi, 'derrotar de un golpe al monstruo');
    t = t.replace(/\blib[eé]\s+(?:al|el)\s+(?:bicho|mob|monstruo)\b/gi, 'usa Liberación sobre el monstruo');
    t = t.replace(/\bcoop\s+(?:al|el)\s+(?:bicho|mob|monstruo)\b/gi, 'usa Cooperación sobre el monstruo');
    t = t.replace(/\bcorrup\s+(?:al|el)\s+boss\b/gi, 'usa Corrupción sobre el boss');

    // Invites, Trade & Crash (ES)
    t = t.replace(/\b(?:bsco|busco)\s+grp\b/gi, 'busco grupo');
    t = t.replace(/\b(?:da|dame|pasen)\s+grp\b/gi, 'invita al grupo');
    t = t.replace(/\b(?:inv|invi)\b/gi, 'invita');
    t = t.replace(/\b(?:manda\s+mp|susurro|wisp|whisp)\b/gi, 'envíame mp');
    t = t.replace(/\bvdo\b/gi, 'vendo');
    t = t.replace(/\b(?:cpo|cmp)\b/gi, 'compro');
    t = t.replace(/\b(?:no\s+regateo|sin\s+regateo|sin\s+rebajas?)\b/gi, 'precio fijo');
    t = t.replace(/\b(?:sin\s+timos|no\s+timo|no\s+estafa)\b/gi, 'sin estafas');
    t = t.replace(/\bfm\b/gi, 'forjamagia');
    t = t.replace(/\bjet\s+perf(?:ecto)?\b/gi, 'tirada perfecta');
    t = t.replace(/\b(?:se\s+me\s+cayo|se\s+cerro|crasheo|crashee)\b/gi, 'mi juego se cerró');
    t = t.replace(/\bme\s+desconecte\b/gi, 'me desconecté');
  }
  return t;
}
