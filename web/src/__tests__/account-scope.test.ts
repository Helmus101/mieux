import { describe, it, expect } from 'vitest';
import { setStorage, setAccountId } from '@shared/storage';
import { useProfile, hydrateProfile } from '@shared/stores/profileStore';
import { useHistory, hydrateHistory } from '@shared/stores/historyStore';

const mem = new Map<string, string>();
setStorage({ getItem: (k) => mem.get(k) ?? null, setItem: (k, v) => { mem.set(k, v); }, removeItem: (k) => { mem.delete(k); }, keys: () => [...mem.keys()] });
const switchTo = (uid: string | null) => { setAccountId(uid); hydrateProfile(); hydrateHistory(); };

describe('per-account local data', () => {
  it('keeps profile and history separate per account and restores them on switch back', () => {
    switchTo('A');
    useProfile.getState().setName('Alice');
    useProfile.getState().finish();
    useHistory.getState().addScan({ id: '111', name: 'Pâtes' });

    switchTo('B');
    expect(useProfile.getState().name).toBe('');
    expect(useProfile.getState().onboarded).toBe(false);
    expect(useHistory.getState().scans).toHaveLength(0);
    useProfile.getState().setName('Bob');
    useHistory.getState().addScan({ id: '222', name: 'Riz' });

    switchTo('A');
    expect(useProfile.getState().name).toBe('Alice');
    expect(useProfile.getState().onboarded).toBe(true);
    expect(useHistory.getState().scans.map((s) => s.id)).toEqual(['111']);

    switchTo('B');
    expect(useProfile.getState().name).toBe('Bob');
    expect(useHistory.getState().scans.map((s) => s.id)).toEqual(['222']);

    switchTo(null);
    expect(useHistory.getState().scans).toHaveLength(0);
  });
});
