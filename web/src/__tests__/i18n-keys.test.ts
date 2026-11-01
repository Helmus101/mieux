import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fr } from '@shared/i18n/fr';

// Every literal t('some.key') used by the web screens and the shared code must exist in the French dictionary.
// (Dynamic keys such as t('priorities.' + k) are checked by the other tests.)
const here = resolve(__dirname, '../..');
const roots = [join(here, 'src'), join(here, '..', 'shared')];
const files = (d: string): string[] => readdirSync(d).flatMap((f) => { const p = join(d, f); return f === 'node_modules' || f === 'node_modules.nosync' || f === '__tests__' ? [] : statSync(p).isDirectory() ? files(p) : /\.(ts|tsx)$/.test(f) ? [p] : []; });
const has = (path: string) => { const v = path.split('.').reduce((o: any, k) => (o == null ? o : o[k]), fr as any); return typeof v === 'string'; };

describe('translation keys', () => {
  it('all literal keys exist', () => {
    const missing: string[] = [];
    for (const r of roots) for (const f of files(r)) {
      const src = readFileSync(f, 'utf8');
      for (const m of src.matchAll(/\bt\('([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)'\s*[,)]/g)) if (!has(m[1])) missing.push(`${f.replace(here, '')}: ${m[1]}`);
    }
    expect(missing).toEqual([]);
  });
});
