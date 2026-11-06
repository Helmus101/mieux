import { beforeEach, describe, expect, it } from 'vitest';

const store: Record<string, string> = {};
(globalThis as any).localStorage = { getItem: (k: string) => store[k] ?? null, setItem: (k: string, v: string) => { store[k] = v; }, removeItem: (k: string) => { delete store[k]; } };

describe('history without an account', () => {
  beforeEach(() => { Object.keys(store).forEach((k) => delete store[k]); });
  it('keeps a scanned product, newest first, once, and persists it', async () => {
    const { useHistory } = await import('@shared/stores/historyStore');
    useHistory.getState().clear();
    useHistory.getState().addScan({ id: '1', name: 'Houmous', brand: 'X' });
    useHistory.getState().addScan({ id: '2', name: 'Cheerios', brand: 'General Mills' });
    useHistory.getState().addScan({ id: '1', name: 'Houmous', brand: 'X' });          // scanned again: moves to the top, no duplicate
    expect(useHistory.getState().scans.map((s) => s.id)).toEqual(['1', '2']);
    expect(useHistory.getState().productById('2')?.name).toBe('Cheerios');
    expect(Object.keys(store).some((k) => k.includes('fiq_h_scans'))).toBe(true);     // written to the device
  });
});
