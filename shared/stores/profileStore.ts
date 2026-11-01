import { create } from 'zustand';
import { load, save } from '../storage';
import { PARIS_DEFAULT } from '../zones';
import { setStrict } from '../config';

export type Diet = 'omnivore' | 'vegetarian' | 'vegan';
export const PRIORITY_KEYS = ['value', 'budget', 'overall', 'sugars', 'protein', 'fibre', 'additives'] as const;
export const ALLERGEN_KEYS = ['gluten', 'milk'] as const; // the two restrictions offered at onboarding; the API accepts all 14 EU allergens

export interface Place { city: string; postcode: string | null; lat?: number; lon?: number; label?: string; exact?: boolean }
interface Profile { onboarded: boolean; priorities: string[]; diet: Diet; allergens: string[]; name?: string; place?: Place | null; chains?: string[]; strictAdditives?: boolean; autoCamera?: boolean }
export interface Zone { lat: number; lon: number; label: string; radius_km: number }
interface State extends Profile {
  estimates: boolean; setEstimates: (v: boolean) => void;
  zone: Zone | null; setZone: (z: Zone | null) => void;
  setName: (n: string) => void; setPlace: (p: Place | null) => void; setStrictAdditives: (v: boolean) => void; setAutoCamera: (v: boolean) => void; toggleChain: (id: string) => void; clearChains: () => void; hydrate: () => void; togglePriority: (k: string) => void; setDiet: (d: Diet) => void; toggleAllergen: (k: string) => void; finish: () => void; reset: () => void;
  compare: string[]; addCompare: (id: string) => void; removeCompare: (id: string) => void; clearCompare: () => void;
}
const KEY = 'fiq_profile';
const init: Profile = load<Profile>(KEY, { onboarded: false, priorities: [], diet: 'omnivore', allergens: [], name: '', place: null, chains: [], strictAdditives: true, autoCamera: false });
setStrict(init.strictAdditives !== false);
const persist = (s: Profile) => save(KEY, { onboarded: s.onboarded, priorities: s.priorities, diet: s.diet, allergens: s.allergens, name: s.name ?? '', place: s.place ?? null, chains: s.chains ?? [], strictAdditives: s.strictAdditives !== false, autoCamera: s.autoCamera === true });

export const useProfile = create<State>((set, get) => ({
  ...init,
  estimates: load<boolean>('fiq_estimates', false), // real data only unless the user opts in
  setEstimates: (v) => { set({ estimates: v }); save('fiq_estimates', v); },
  zone: load<Zone | null>('fiq_zone', PARIS_DEFAULT), // Paris by default
  setZone: (z) => { set({ zone: z }); save('fiq_zone', z); },
  compare: load<string[]>('fiq_compare', []),
  // At most two priorities: picking a third replaces the oldest.
  setName: (n) => { set({ name: n }); persist({ ...get(), name: n }); },
  setAutoCamera: (v) => { set({ autoCamera: v }); persist({ ...get(), autoCamera: v }); },
  setStrictAdditives: (v) => { setStrict(v); set({ strictAdditives: v }); persist({ ...get(), strictAdditives: v }); },
  toggleChain: (id) => { const cur = get().chains ?? []; const next = cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]; set({ chains: next }); persist({ ...get(), chains: next }); },
  clearChains: () => { set({ chains: [] }); persist({ ...get(), chains: [] }); },
  setPlace: (p) => { set({ place: p }); persist({ ...get(), place: p }); },
  hydrate: () => { const p = load<Profile>(KEY, init); setStrict(p.strictAdditives !== false); set({ ...p, zone: load<Zone | null>('fiq_zone', PARIS_DEFAULT), estimates: load<boolean>('fiq_estimates', false), compare: load<string[]>('fiq_compare', []) }); },
  togglePriority: (k) => { if (k === 'eco') return; const p = get().priorities; const n = p.includes(k) ? p.filter((x) => x !== k) : [...p, k].slice(-2); set({ priorities: n }); persist({ ...get(), priorities: n }); },
  setDiet: (d) => { set({ diet: d }); persist({ ...get(), diet: d }); },
  toggleAllergen: (k) => { const a = get().allergens; const n = a.includes(k) ? a.filter((x) => x !== k) : [...a, k]; set({ allergens: n }); persist({ ...get(), allergens: n }); },
  finish: () => { set({ onboarded: true }); persist({ ...get(), onboarded: true }); },
  reset: () => { set({ onboarded: false }); persist({ ...get(), onboarded: false }); },
  addCompare: (id) => { const c = get().compare.includes(id) ? get().compare : [...get().compare, id].slice(-4); set({ compare: c }); save('fiq_compare', c); },
  removeCompare: (id) => { const c = get().compare.filter((x) => x !== id); set({ compare: c }); save('fiq_compare', c); },
  clearCompare: () => { set({ compare: [] }); save('fiq_compare', []); },
}));

/** What the API needs, derived from the saved profile (budget/overall/additives are ranking priorities, the rest are fit checks). */
export const apiPrefs = (p: Pick<Profile, 'priorities' | 'diet' | 'allergens'>) => ({ diet: p.diet, priorities: p.priorities, allergens: p.allergens });
