import { beforeEach, describe, expect, it } from 'vitest';
import { setStorage, load, save, clearAll } from '@shared/storage';
import { t } from '@shared/i18n';
import { additiveInfo } from '@shared/additives';
import { formatCents } from '@shared/utils/format';

// In-memory storage adapter, exactly like the one the Expo app installs after preloading AsyncStorage.
const mem = new Map<string, string>();
setStorage({ getItem: (k) => mem.get(k) ?? null, setItem: (k, v) => void mem.set(k, v), removeItem: (k) => void mem.delete(k), keys: () => [...mem.keys()] });
beforeEach(() => mem.clear());

describe('storage adapter', () => {
  it('round-trips JSON and returns the default when missing', () => {
    expect(load('fiq_x', 7)).toBe(7);
    save('fiq_x', { a: [1, 2] });
    expect(load('fiq_x', null)).toEqual({ a: [1, 2] });
  });
  it('accepts a legacy raw string for string defaults (old session ids)', () => {
    mem.set('fiq_session_id', 'anon-abc');
    expect(load<string | null>('fiq_session_id', null)).toBe('anon-abc');
  });
  it('clearAll removes only fiq_ keys', () => {
    save('fiq_a', 1); save('other', 2); clearAll();
    expect([...mem.keys()]).toEqual(['other']);
  });
});

describe('i18n', () => {
  it('formats variables and falls back to the key for unknown paths', () => {
    expect(t('home.boughtN', { n: 3 })).toBe('acheté 3 fois');
    expect(t('does.not.exist')).toBe('does.not.exist');
  });
});

describe('format', () => {
  it('uses a decimal comma and the euro sign', () => {
    expect(formatCents(445)).toBe('4,45 €');
    expect(formatCents(0)).toBe('0,00 €');
  });
});

describe('additives', () => {
  it('knows E330 and does not pretend to know others', () => {
    expect(additiveInfo('E330')?.name).toBe('Acide citrique');
    expect(additiveInfo('e999999')).toBeNull();
  });
});

describe('profile store', () => {
  it('keeps at most two priorities (a third replaces the oldest) and ignores the read-only eco priority', async () => {
    const { useProfile } = await import('@shared/stores/profileStore');
    const s = useProfile.getState();
    s.togglePriority('protein'); s.togglePriority('sugars'); s.togglePriority('fibre');
    expect(useProfile.getState().priorities).toEqual(['sugars', 'fibre']);
    s.togglePriority('eco');
    expect(useProfile.getState().priorities).toEqual(['sugars', 'fibre']);
  });
  it('hydrate re-reads values written by another storage adapter', async () => {
    const { useProfile } = await import('@shared/stores/profileStore');
    save('fiq_profile', { onboarded: true, priorities: ['budget'], diet: 'vegan', allergens: ['milk'] });
    useProfile.getState().hydrate();
    const p = useProfile.getState();
    expect(p.onboarded).toBe(true); expect(p.diet).toBe('vegan'); expect(p.allergens).toEqual(['milk']);
  });
});

describe('history store', () => {
  it('stores a product snapshot so the page works offline, and de-duplicates scans', async () => {
    const { useHistory } = await import('@shared/stores/historyStore');
    const h = useHistory.getState();
    h.addScan({ id: '1', name: 'A' }); h.addScan({ id: '2', name: 'B' }); h.addScan({ id: '1', name: 'A2' });
    const scans = useHistory.getState().scans;
    expect(scans.map((x) => x.id)).toEqual(['1', '2']);
    expect(useHistory.getState().productById('1').name).toBe('A2');
  });
});
