/**
 * Normalizes common English video game chat abbreviations
 * strictly into standard English (never injects French words before translation).
 */
export function normalizeEnglishGamingChat(text: string): string {
  if (!text) return '';
  let t = text;

  t = t.replace(/\bfarmin\b/gi, 'farming');
  t = t.replace(/\b(?:plz|pls)\b/gi, 'please');
  t = t.replace(/\b(?:thx|ty)\b/gi, 'thank you');
  t = t.replace(/\b(?:lv+l)\b/gi, 'level');
  t = t.replace(/\b(?:fri\s*3|f3)\b/gi, 'Frigost 3');
  t = t.replace(/\b(?:fri\s*2|f2)\b/gi, 'Frigost 2');
  t = t.replace(/\b(?:fri\s*1|f1)\b/gi, 'Frigost 1');
  t = t.replace(/\b(\d+)\s*m(\d+)\b/gi, '$1.$2M kamas');
  t = t.replace(/(\d+(?:[.,]\d+)?)\s*mk\b/gi, '$1M kamas');
  t = t.replace(/(\d+(?:[.,]\d+)?)\s*kk\b/gi, '$1k kamas');
  t = t.replace(/\bhs\b/gi, 'haven bag');
  t = t.replace(/\br\s+u\b/gi, 'are you');
  t = t.replace(/\bu\s+r\b/gi, 'you are');
  t = t.replace(/\b(?:im|i'm)\b/gi, 'I am');
  t = t.replace(/\bidk\b/gi, "I don't know");
  t = t.replace(/\bnp\b/gi, 'no problem');
  t = t.replace(/\bomw\b/gi, 'on my way');
  t = t.replace(/\bbrb\b/gi, 'be right back');
  t = t.replace(/\b(?:inv|invi)\b/gi, 'invite');
  t = t.replace(/\bdg\b/gi, 'dungeon');

  return t;
}
