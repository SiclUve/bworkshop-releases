import { describe, it, expect } from 'vitest';
import { assessMessageIntelligibility } from '../../src/utils/universalTranslator';
import { loadTestEntries } from '../helpers/loadEntries';

const entries = loadTestEntries();

describe('Incomprehensible / Ultra-Slang Escalation Gate', () => {
  it('does NOT escalate normal or already-normalized Dofus sentences across all 4 languages', () => {
    const normalCases: [string, 'fr' | 'en' | 'es' | 'pt'][] = [
      ['taper un gourlot ça te dit ?', 'fr'],
      ['on va taper les mobs ravageurs', 'fr'],
      ["s'il te plaît, j'ai besoin d'aide pour le donjon Comte Harebourg", 'fr'],
      ['cherche 2 rox pour nidas', 'fr'],
      ['LF 2 spots for Dragon Pig dungeon pls', 'en'],
      ['WTB Royal Gobball set 2mk firm price', 'en'],
      ['busco 2 cupos para mazmo dragocerdo xfa', 'es'],
      ['vendo set jalato real 3mk sin regateo', 'es'],
      ['procuro vaga pra cala papatudo real pfv', 'pt'],
      ['estou indo pelo zaap obrigado', 'pt']
    ];

    for (const [text, lang] of normalCases) {
      const res = assessMessageIntelligibility(text, lang, entries);
      expect(res.isIncomprehensible, `False positive on "${text}" (${res.reasons.join(', ')})`).toBe(false);
    }
  });

  it('flags genuinely incomprehensible / heavy ultra-slang / cryptic SMS messages for AI rescue', () => {
    const hardCases: [string, 'fr' | 'es' | 'pt'][] = [
      ['wsh frr le sram il a pa capte la strat il c fet os mskn', 'fr'],
      ['jv fr un trc vitef jsui pa stuff dtt chpr mdrrrr', 'fr'],
      ['oe weon q hacemos con el pibe q manco ql csm', 'es'],
      ['mano mlk o boss ta bugado dms n da pra tankar aff kkkk', 'pt']
    ];

    for (const [text, lang] of hardCases) {
      const res = assessMessageIntelligibility(text, lang, entries);
      expect(res.isIncomprehensible, `Missed incomprehensible phrase "${text}" (score=${res.score})`).toBe(true);
    }
  });

  it('escalates when GTX passes multiple unrecognized tokens through verbatim', () => {
    const input = 'frr chpr il a zgeg le mob';
    const gtxOut = 'frr chpr he zgeg the mob';
    const res = assessMessageIntelligibility(input, 'fr', entries, gtxOut, 'en');
    expect(res.isIncomprehensible).toBe(true);
    expect(res.reasons.some((r) => r.startsWith('gtx_untranslated_tokens'))).toBe(true);
  });

  it('never escalates empty strings, coordinates, or pure bracketed item links', () => {
    for (const trivial of ['', '   ', '[12, -24]', '[Voile d\'encre] 2mk', '/w *Pseudo* salut!']) {
      const res = assessMessageIntelligibility(trivial, 'fr', entries);
      expect(res.isIncomprehensible, `Unexpected escalation on "${trivial}"`).toBe(false);
    }
  });
});
