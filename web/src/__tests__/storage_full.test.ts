import { describe, expect, it } from 'vitest';

// A browser storage of 100 characters: the disposable cache must give way to the person's history and settings.
const store: Record<string, string> = {};
const used = () => Object.entries(store).reduce((n, [k, v]) => n + k.length + v.length, 0);
(globalThis as any).localStorage = {
  getItem: (k: string) => store[k] ?? null,
  setItem: (k: string, v: string) => { const after = used() - (k in store ? k.length + store[k].length : 0) + k.length + v.length; if (after > 100) throw new Error('QuotaExceededError'); store[k] = v; },
  removeItem: (k: string) => { delete store[k]; },
};
Object.defineProperty(globalThis.localStorage, 'length', { get: () => Object.keys(store).length });
(globalThis.localStorage as any).key = (i: number) => Object.keys(store)[i] ?? null;
Object.keys = ((orig) => (o: object) => (o === (globalThis as any).localStorage ? Object.keys(store) : orig(o)))(Object.keys);

describe('full browser storage', () => {
  it('drops the cache and still saves the history', async () => {
    const { save, load } = await import('@shared/storage');
    store['mx_swr_prod:1'] = 'x'.repeat(80);                      // the cache fills the storage
    save('fiq_h_scans', [{ id: '1' }]);                           // the history must still be saved
    expect(load('fiq_h_scans', [])).toEqual([{ id: '1' }]);
    expect(store['mx_swr_prod:1']).toBeUndefined();               // ...at the cost of the cache
  });
});
