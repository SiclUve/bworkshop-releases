import * as fs from 'fs';
import * as path from 'path';
import { DofusEntry } from '../../src/types/dofus';
import { getAllExpandedDofusEntries } from '../../src/data/dofusQuestsAndBounties';

let cached: DofusEntry[] | null = null;

export function loadTestEntries(): DofusEntry[] {
  if (cached) return cached;
  const root = path.resolve(__dirname, '../..');
  const encPath = path.join(root, 'public/assets/dofus_official_encyclopedia.json');
  const commPath = path.join(root, 'public/assets/community-dictionary.json');

  const enc = fs.existsSync(encPath) ? JSON.parse(fs.readFileSync(encPath, 'utf8')).entries || [] : [];
  const comm = fs.existsSync(commPath) ? JSON.parse(fs.readFileSync(commPath, 'utf8')).entries || [] : [];

  cached = [...comm, ...enc, ...getAllExpandedDofusEntries()];
  return cached;
}
