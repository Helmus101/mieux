import { create } from 'zustand';
import { api } from '../api/client';
import { load, save } from '../storage';
import { PARIS_DEFAULT } from '../zones';
import { setStrict } from '../config';

export type Diet = 'omnivore' | 'vegetarian' | 'vegan';
export type Language = 'fr' | 'en';
export const PRIORITY_KEYS = ['value', 'budget', 'overall', 'sugars', 'protein', 'fibre', 'additives'] as const;
export const ALLERGEN_KEYS = ['gluten', 'milk'] as const; // the two restrictions offered at onboarding; the API accepts all 14 EU allergens

export interface Place { city: string; postcode: string | null; lat?: number; lon?: number; label?: string; exact?: boolean }
interface Profile { onboarded: boolean; priorities: string[]; diet: Diet; allergens: string[]; name?: string; place?: Place | null; chains?: string[]; strictAdditives?: boolean; autoCamera?: boolean; language?: Language }
export interface Zone { lat: number; lon: number; label: string; radius_km: number }
interface State extends Profile {
  estimates: boolean; setEstimates: (v: boolean) => void;
  zone: Zone | null; setZone: (z: Zone | null) => void;
  setName: (n: string) => void; setPlace: (p: Place | null) => void; setStrictAdditives: (v: boolean) => void; setAutoCamera: (v: boolean) => void; setLanguage: (l: Language) => void; toggleChain: (id: string) => void; removeChain: (id: string) => void; setChains: (ids: string[]) => void; clearChains: () => void; hydrate: () => void; togglePriority: (k: string) => void; setDiet: (d: Diet) => void; toggleAllergen: (k: string) => void; finish: () => void; reset: () => void;
  compare: string[]; addCompare: (id: string) => void; removeCompare: (id: string) => void; clearCompare: () => void;
}
const platformOf = (): string => {
  if (typeof navigator === 'undefined') return 'web';
  const nav = navigator as unknown as { userAgent?: string; product?: string };
  if (nav.product === 'ReactNative') return 'native';
  const ua = nav.userAgent ?? '';
  if (/iPhone|iPad|iPod/.test(ua)) return 'ios';
  return /Android/i.test(ua) ? 'android' : 'web';
};
// Only the first name and city are sent to the server, so the owner can see who uses Mieux without an account.
// Scans, receipts and prices never go through this call. Debounced: the name field saves on every keystroke.
let pushTimer: ReturnType<typeof setTimeout> | null = null;
const pushIdentity = (s: Profile) => {
  if (pushTimer) clearTimeout(pushTimer);
  pushTimer = setTimeout(() => {
    pushTimer = null;
    api.putIdentity({ name: s.name || null, city: s.place?.city ?? null, postcode: s.place?.postcode ?? null, platform: platformOf() })
      .catch(() => undefined);           // offline or server restarting: the local profile stays the source of truth
  }, 1500);
};
const init: Profile = { onboarded: false, priorities: [], diet: 'omnivore', allergens: [], name: '', place: null, chains: [], strictAdditives: true, autoCamera: false, language: 'fr' };
// Always use strict mode (Yuka-like) by default
setStrict(true);
const persist = (s: Profile) => {
  save('fiq_profile', { onboarded: s.onboarded, priorities: s.priorities, diet: s.diet, allergens: s.allergens, name: s.name ?? '', place: s.place ?? null, chains: s.chains ?? [], strictAdditives: true, autoCamera: s.autoCamera === true, language: s.language ?? 'fr' });
  pushIdentity(s);
};

export const useProfile = create<State>((set, get) => {
  const loaded = load<Profile>('fiq_profile', init);
  return {
    ...loaded,
    estimates: load<boolean>('fiq_estimates', false), // real data only unless the user opts in
    setEstimates: (v) => { set({ estimates: v }); save('fiq_estimates', v); },
    zone: load<Zone | null>('fiq_zone', PARIS_DEFAULT), // Paris by default
    setZone: (z) => { set({ zone: z }); save('fiq_zone', z); },
    compare: load<string[]>('fiq_compare', []),
    // At most two priorities: picking a third replaces the oldest.
    setName: (n) => { set({ name: n }); persist({ ...get(), name: n }); },
    setAutoCamera: (v) => { set({ autoCamera: v }); persist({ ...get(), autoCamera: v }); },
    setLanguage: (l) => { set({ language: l }); persist({ ...get(), language: l }); },
    setStrictAdditives: () => { setStrict(true); set({ strictAdditives: true }); persist({ ...get(), strictAdditives: true }); },
    toggleChain: (id) => { const cur = get().chains ?? []; const next = cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]; set({ chains: next }); persist({ ...get(), chains: next }); },
    removeChain: (id) => { const cur = get().chains ?? []; const next = cur.filter((x) => x !== id); set({ chains: next }); persist({ ...get(), chains: next }); },
    setChains: (ids) => { set({ chains: ids }); persist({ ...get(), chains: ids }); },
    clearChains: () => { set({ chains: [] }); persist({ ...get(), chains: [] }); },
    setPlace: (p) => { set({ place: p }); persist({ ...get(), place: p }); },
    hydrate: () => { const p = load<Profile>('fiq_profile', init); setStrict(true); set({ ...p, zone: load<Zone | null>('fiq_zone', PARIS_DEFAULT), estimates: load<boolean>('fiq_estimates', false), compare: load<string[]>('fiq_compare', []), priorities: p.priorities ?? [], strictAdditives: true, autoCamera: p.autoCamera === true, language: p.language ?? 'fr' }); },
    togglePriority: (k) => { if (k === 'eco') return; const p = get().priorities; const n = p.includes(k) ? p.filter((x) => x !== k) : [...p, k].slice(-2); set({ priorities: n }); persist({ ...get(), priorities: n }); },
    setDiet: (d) => { set({ diet: d }); persist({ ...get(), diet: d }); },
    toggleAllergen: (k) => { const a = get().allergens; const n = a.includes(k) ? a.filter((x) => x !== k) : [...a, k]; set({ allergens: n }); persist({ ...get(), allergens: n }); },
    finish: () => { set({ onboarded: true }); persist({ ...get(), onboarded: true }); },
    reset: () => { set({ ...init, onboarded: false }); persist({ ...init, onboarded: false }); },
    addCompare: (id) => { const c = get().compare.includes(id) ? get().compare : [...get().compare, id].slice(-4); set({ compare: c }); save('fiq_compare', c); },
    removeCompare: (id) => { const c = get().compare.filter((x) => x !== id); set({ compare: c }); save('fiq_compare', c); },
    clearCompare: () => { set({ compare: [] }); save('fiq_compare', []); },
  };
});

/** What the API needs, derived from the saved profile (budget/overall/additives are ranking priorities, the rest are fit checks). */
export const apiPrefs = (p: Pick<Profile, 'priorities' | 'diet' | 'allergens'>) => ({ diet: p.diet, priorities: p.priorities, allergens: p.allergens });

/** Reload the profile for a specific account (called when account changes). */
export const hydrateProfile = () => {
  const p = load<Profile>('fiq_profile', init);
  setStrict(true);
  useProfile.setState({
    ...p,
    zone: load<Zone | null>('fiq_zone', PARIS_DEFAULT),
    estimates: load<boolean>('fiq_estimates', false),
    compare: load<string[]>('fiq_compare', []),
    priorities: p.priorities ?? [],
    strictAdditives: true,
    autoCamera: p.autoCamera === true,
    language: p.language ?? 'fr'
  });
};
