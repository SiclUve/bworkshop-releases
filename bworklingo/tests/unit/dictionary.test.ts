import { describe, it, expect } from 'vitest';
import { CATEGORY_LABELS, getCategoryLabel } from '../../src/data/dofusDictionary';

describe('Dictionary category translations', () => {
  it('provides localized labels for FR, EN, ES, and PT on every category', () => {
    const keys = Object.keys(CATEGORY_LABELS);
    expect(keys.length).toBeGreaterThanOrEqual(16);

    for (const key of keys) {
      for (const lang of ['fr', 'en', 'es', 'pt'] as const) {
        const label = getCategoryLabel(key, lang);
        expect(label, `Missing ${lang} label for ${key}`).toBeTruthy();
        expect(label).not.toBe(key);
      }
    }

    expect(getCategoryLabel('quests', 'en')).toBe('Quests & Dofus');
    expect(getCategoryLabel('smithmagic', 'es')).toBe('Forjamagia (FM)');
    expect(getCategoryLabel('dungeons_and_social', 'pt')).toBe('Calabouços & Social');
  });
});
