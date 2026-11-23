import { describe, it, expect } from 'vitest';
import {
  normalizeFrenchGamingChat,
  normalizeEnglishGamingChat,
  normalizeIberianGamingChat,
  normalizeChatForLanguage,
  guessChatLanguage
} from '../../src/utils/universalTranslator';

describe('French gaming chat normalizer', () => {
  it('normalizes typos, phonetic verbs, and gaming slang', () => {
    expect(normalizeFrenchGamingChat('taper un gourlot ça te dit ?')).toBe('combattre Gourlo ça te dit ?');
  });

  it('normalizes key FR gamer phrases consistently', () => {
    expect(normalizeFrenchGamingChat('taper un gourlo sa te dit')).toBe('combattre Gourlo ça te dit');
    expect(normalizeFrenchGamingChat('qui pour taper gourlot')).toBe('qui veut faire Gourlo le Terrible');
    expect(normalizeFrenchGamingChat('ki e cho pr fri3 ?')).toBe('qui est chaud pour Frigost 3 ?');
    expect(normalizeFrenchGamingChat('sa vaut cb ?')).toBe('combien ça vaut ?');
    expect(normalizeFrenchGamingChat('attention au cac')).toBe('attention au corps-à-corps');
    expect(normalizeFrenchGamingChat("j'ai crash je reco")).toBe('mon jeu a planté je me reconnecte');
    expect(normalizeFrenchGamingChat('2m5 ou 500kk')).toBe('2.5M kamas ou 500k kamas');
    expect(normalizeFrenchGamingChat('voile dencre jet perf?')).toContain("Voile d'encre");
    expect(normalizeFrenchGamingChat('rdv zaap village')).toBe('rendez-vous au zaap village');
    expect(normalizeFrenchGamingChat('dj rdv')).toBe('donjon Reine des Voleurs');
  });
});

describe('English gaming chat normalizer', () => {
  it('normalizes abbreviations strictly into standard English', () => {
    expect(normalizeEnglishGamingChat('farmin fri3 plz thx')).toBe('farming Frigost 3 please thank you');
    expect(normalizeEnglishGamingChat('omw back to hs 2mk')).toBe('on my way back to haven bag 2M kamas');
    expect(normalizeEnglishGamingChat('r u ready idk brb')).toBe("are you ready I don't know be right back");
    expect(normalizeEnglishGamingChat('inv to dg')).toBe('invite to dungeon');
  });
});

describe('Spanish (ES) gaming chat normalizer', () => {
  it('normalizes ES SMS typos, dungeons, collectors, and trade', () => {
    expect(normalizeIberianGamingChat('wenas bsco grp pa mazmo dc xfa', 'es')).toBe(
      'hola busco grupo para mazmorra dc por favor'
    );
    expect(normalizeIberianGamingChat('quedan 2 cupos para mazmos', 'es')).toBe(
      'quedan 2 plazas para mazmorras'
    );
    expect(normalizeIberianGamingChat('defensa de recas y perco', 'es')).toBe(
      'defensa de recaudadores y recaudador'
    );
    expect(normalizeIberianGamingChat('vdo set jalato 2m5 no regateo sin timos', 'es')).toBe(
      'vendo set de Jalató 2.5M kamas precio fijo sin estafas'
    );
    expect(normalizeIberianGamingChat('100kk c/u grax ntp', 'es')).toBe(
      '100k kamas cada uno gracias no te preocupes'
    );
    expect(normalizeIberianGamingChat('toy sin al y sin ldv en el bicho', 'es')).toBe(
      'estoy falta de alcance y sin línea de visión en el monstruo'
    );
  });

  it('does NOT confuse AP ("PA") stat with Spanish preposition "pa" -> "para"', () => {
    expect(normalizeIberianGamingChat('vendo anillo exo pa y pozo pa', 'es')).toBe(
      'vendo anillo exo pa y pozo pa'
    );
    expect(normalizeIberianGamingChat('ret pa al boss', 'es')).toBe('reducción de PA al boss');
  });
});

describe('Portuguese (PT-BR) gaming chat normalizer', () => {
  it('normalizes PT-BR SMS slang, dungeons, collectors, and trade', () => {
    expect(normalizeIberianGamingChat('qm topa cala pfv vlw', 'pt')).toBe(
      'quem topa calabouço por favor obrigado'
    );
    expect(normalizeIberianGamingChat('prc grp pra dg f3 tmj', 'pt')).toBe(
      'procuro grupo para calabouço Frigost 3 estamos juntos'
    );
    expect(normalizeIberianGamingChat('percs atacados, ajuda aki agr', 'pt')).toBe(
      'coletores atacados, ajuda aqui agora'
    );
    expect(normalizeIberianGamingChat('vdo conj papatudo real 3mk sem choro sem golpe', 'pt')).toBe(
      'vendo conjunto de Papatudo Real 3M kamas preço fixo sem golpes'
    );
    expect(normalizeIberianGamingChat('levei dc meu jogo travou flw', 'pt')).toBe(
      'meu jogo travou meu jogo travou até mais'
    );
    expect(normalizeIberianGamingChat('100kk c/u blz', 'pt')).toBe(
      '100k kamas cada um combinado'
    );
  });

  it('keeps "dps" untouched so DPS role is never rewritten to "depois"', () => {
    expect(normalizeIberianGamingChat('procuro 2 dps pra dg', 'pt')).toBe('procuro 2 dps para calabouço');
  });
});

describe('Auto language guesser prevents cross-language collision', () => {
  it('identifies FR, EN, ES, PT accurately', () => {
    expect(guessChatLanguage('qui pour taper un gourlot svp ?')).toBe('fr');
    expect(guessChatLanguage('LF 2 spots for Dragon Pig dungeon pls')).toBe('en');
    expect(guessChatLanguage('busco 1 cupo para mazmorra xfa')).toBe('es');
    expect(guessChatLanguage('procuro vaga pra cala obg vlw')).toBe('pt');
  });

  it('normalizes "inv" correctly per detected language in auto mode', () => {
    expect(normalizeChatForLanguage('please inv to dungeon', 'auto').normalized).toBe('please invite to dungeon');
    expect(normalizeChatForLanguage('porfa inv a mazmo', 'auto').normalized).toBe('por favor invita a mazmorra');
    expect(normalizeChatForLanguage('pfv inv pra cala', 'auto').normalized).toBe('por favor convida para calabouço');
  });
});
