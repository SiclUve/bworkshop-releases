import { describe, it, expect } from 'vitest';
import { translateNeuralDofusClient } from '../../src/utils/universalTranslator';
import { loadTestEntries } from '../helpers/loadEntries';

const entries = loadTestEntries();

describe('Live GTX Neural Dofus Translation (FR/EN/ES/PT)', () => {
  it('handles FR gaming idioms & monster families without regression', async () => {
    const cases: [string, 'fr' | 'en' | 'es' | 'pt', 'fr' | 'en' | 'es' | 'pt', string, string?][] = [
      ['taper un gourlot ça te dit ?', 'fr', 'en', 'Gourlo', 'neck'],
      ['on va taper les mobs ravageurs', 'fr', 'en', 'Destroyer', 'pest'],
      ['attention au cac', 'fr', 'en', 'melee', 'poop'],
      ['busco 2 cupos para mazmo dragocerdo xfa', 'es', 'en', 'Dragon Pig', 'pest'],
      ['procuro 2 vagas pra cala papatudo real pfv', 'pt', 'en', 'Royal Gobball', 'pest'],
      ['recrute roublard pour les ravageurs', 'fr', 'es', 'Tymador', 'plagas'],
      ['recrute ouginak pour les ravageurs', 'fr', 'pt', 'Kilorf', 'pragas']
    ];

    for (const [text, src, tgt, expected, forbidden] of cases) {
      const res = await translateNeuralDofusClient(text, entries, src, tgt);
      expect(res).toBeTruthy();
      const lower = (res || '').toLowerCase();
      expect(lower).toContain(expected.toLowerCase());
      if (forbidden) expect(lower).not.toContain(forbidden.toLowerCase());
    }
  }, 25000);
});
