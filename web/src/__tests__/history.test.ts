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

describe('saved list', () => {
  beforeEach(() => { Object.keys(store).forEach((k) => delete store[k]); });
  it('saves, toggles, saves many without duplicates, survives clearing the history, and persists', async () => {
    const { useHistory } = await import('@shared/stores/historyStore');
    const h = () => useHistory.getState();
    h().clearSaved();
    h().toggleSaved({ id: '1', name: 'A' });
    h().saveMany([{ id: '1', name: 'A' }, { id: '2', name: 'B' }, { id: '3', name: 'C' }, { name: 'no id' }]);
    expect(h().saved.map((s) => s.id).sort()).toEqual(['1', '2', '3']);
    h().toggleSaved({ id: '2', name: 'B' });                                           // toggling a saved product removes it
    expect(h().saved.map((s) => s.id).sort()).toEqual(['1', '3']);
    h().addScan({ id: '9', name: 'scanned' }); h().clear();                           // clearing the history keeps the saved list
    expect(h().saved).toHaveLength(2);
    expect(Object.keys(store).some((k) => k.includes('fiq_h_saved'))).toBe(true);
    h().removeSaved('1');
    expect(h().saved.map((s) => s.id)).toEqual(['3']);
  });
});
