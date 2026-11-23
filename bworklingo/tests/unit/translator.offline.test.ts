import { describe, it, expect } from 'vitest';
import { translateUniversally } from '../../src/utils/universalTranslator';
import { loadTestEntries } from '../helpers/loadEntries';

const entries = loadTestEntries();

describe('Offline Universal Translator — FR <-> EN', () => {
  it('translates monster families accurately without "pest" / "bear cub" / "sleeve"', () => {
    const cases: [string, string, string?][] = [
      ['les mobs ravageurs', 'Destroyer', 'pest'],
      ['un ravageur', 'Destroyer', 'pest'],
      ['famille des ravageurs', 'Destroyer', 'pest'],
      ['on va taper les mobs ravageurs', 'Destroyer', 'pest'],
      ['les gloursons', 'Bearbarians', 'bear cub'],
      ['les mansots', 'Pingwins', 'sleeve'],
      ['les boufmouths', 'Mastogobs']
    ];
    for (const [input, expected, forbidden] of cases) {
      const out = translateUniversally(input, entries, 'fr', 'en').toLowerCase();
      expect(out).toContain(expected.toLowerCase());
      if (forbidden) expect(out).not.toContain(forbidden.toLowerCase());
    }
  });

  it('translates EN -> FR monster families and gaming terms', () => {
    expect(translateUniversally('the Destroyer mobs', entries, 'en', 'fr').toLowerCase()).toContain('mobs ravageurs');
    expect(translateUniversally('Destroyers family', entries, 'en', 'fr').toLowerCase()).toContain('famille des ravageurs');
    expect(translateUniversally('the Bearbarians', entries, 'en', 'fr').toLowerCase()).toContain('gloursons');
    expect(translateUniversally('LF 2 spots melee', entries, 'en', 'fr').toLowerCase()).toContain('cherche 2 places cac');
    expect(translateUniversally('WTB exo AP', entries, 'en', 'fr').toLowerCase()).toContain('achète exo pa');
  });

  it('guards against 2-letter false matches ("am" != Lethal Attack) and /g lastIndex bugs', () => {
    const first = translateUniversally('i am looking for group', entries, 'en', 'fr');
    const second = translateUniversally('i am looking for group', entries, 'en', 'fr');
    expect(first).toBe(second);
    expect(first.toLowerCase()).not.toContain('attaque mortelle');
  });

  it('preserves chat command prefixes and bracketed entities', () => {
    const cmdOut = translateUniversally('/w *Player* cherche 2 places ravageurs', entries, 'fr', 'en');
    expect(cmdOut.startsWith('/w *Player* ')).toBe(true);
    expect(cmdOut.toLowerCase()).toContain('destroyers');
  });
});

describe('Offline Universal Translator — ES & PT pairs', () => {
  it('translates ES -> FR and ES -> EN for dungeons, classes, bosses, and collectors', () => {
    const esToFr = translateUniversally('busco 2 cupos para mazmo dragocerdo xfa', entries, 'es', 'fr').toLowerCase();
    expect(esToFr).toContain('cherche');
    expect(esToFr).toContain('2 places');
    expect(esToFr).toContain('dragon cochon');

    const esToEn = translateUniversally('recluto tymador para recaudador sin regateo', entries, 'es', 'en').toLowerCase();
    expect(esToEn).toContain('recruiting');
    expect(esToEn).toContain('rogue');
    expect(esToEn).toContain('perceptor');
    expect(esToEn).toContain('firm price');

    const esDevToEn = translateUniversally('busco grupo para los devastadores', entries, 'es', 'en').toLowerCase();
    expect(esDevToEn).toContain('destroyers');
    expect(esDevToEn).not.toContain('pest');
  });

  it('translates PT -> FR and PT -> EN for dungeons, classes, bosses, and collectors', () => {
    const ptToFr = translateUniversally('procuro 2 vagas pra cala papatudo real pfv', entries, 'pt', 'fr').toLowerCase();
    expect(ptToFr).toContain('cherche');
    expect(ptToFr).toContain('2 places');
    expect(ptToFr).toContain('bouftou royal');

    const ptToEn = translateUniversally('recruto ladino e kilorf para coletor vlw', entries, 'pt', 'en').toLowerCase();
    expect(ptToEn).toContain('recruiting');
    expect(ptToEn).toContain('rogue');
    expect(ptToEn).toContain('ouginak');
    expect(ptToEn).toContain('perceptor');
    expect(ptToEn).toContain('thank you');
  });

  it('translates FR -> ES and FR -> PT for classes, bosses, and families', () => {
    const frToEs = translateUniversally('cherche roublard pour donjon dragon cochon svp', entries, 'fr', 'es').toLowerCase();
    expect(frToEs).toContain('busco');
    expect(frToEs).toContain('tymador');
    expect(frToEs).toContain('dragocerdo');

    const frToPt = translateUniversally('cherche ouginak pour les ravageurs svp', entries, 'fr', 'pt').toLowerCase();
    expect(frToPt).toContain('procuro');
    expect(frToPt).toContain('kilorf');
    expect(frToPt).toContain('devastadores');
  });

  it('translates directly between ES and PT in both directions', () => {
    const esToPt = translateUniversally('busco 2 cupos para mazmo dragocerdo xfa', entries, 'es', 'pt').toLowerCase();
    expect(esToPt).toContain('procuro');
    expect(esToPt).toContain('2 vagas');
    expect(esToPt).toContain('cala');
    expect(esToPt).toContain('por favor');

    const ptToEs = translateUniversally('recruto ladino para coletor agora vlw', entries, 'pt', 'es').toLowerCase();
    expect(ptToEs).toContain('recluto');
    expect(ptToEs).toContain('tymador');
    expect(ptToEs).toContain('recaudador');
    expect(ptToEs).toContain('gracias');
  });

  it('supports auto-detection end-to-end across FR, EN, ES, and PT', () => {
    const autoFrToEn = translateUniversally('cherche 2 places ravageurs svp', entries, 'auto', 'en').toLowerCase();
    expect(autoFrToEn).toContain('looking for');
    expect(autoFrToEn).toContain('destroyers');

    const autoEsToFr = translateUniversally('busco grupo para mazmorra xfa', entries, 'auto', 'fr').toLowerCase();
    expect(autoEsToFr).toContain('cherche');
    expect(autoEsToFr).toContain('donjon');

    const autoPtToEn = translateUniversally('procuro vaga pra cala pfv vlw', entries, 'auto', 'en').toLowerCase();
    expect(autoPtToEn).toContain('looking for');
    expect(autoPtToEn).toContain('dungeon');
    expect(autoPtToEn).toContain('thank you');
  });
});
