// Tiny storage adapter. Web: localStorage (default). Expo: call setStorage() once at startup with an adapter that has been
// preloaded from AsyncStorage (see mobile/src/storage.ts), then call hydrateStores() so the zustand stores re-read it.
export interface KV { getItem(k: string): string | null; setItem(k: string, v: string): void; removeItem(k: string): void; keys?(): string[] }
let kv: KV = {
  getItem: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
  setItem: (k, v) => { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
  removeItem: (k) => { try { localStorage.removeItem(k); } catch { /* ignore */ } },
  keys: () => { try { return Object.keys(localStorage); } catch { return []; } },
};
export const setStorage = (s: KV) => { kv = s; };
/** Reads JSON. Tolerates a legacy raw string value when the default is a string/null (older versions stored the session id unquoted). */
export const load = <T,>(k: string, d: T): T => {
  const raw = kv.getItem(k);
  if (raw == null) return d;
  try { return JSON.parse(raw) as T; } catch { return (typeof d === 'string' || d === null ? (raw as unknown as T) : d); }
};
export const save = (k: string, v: unknown) => kv.setItem(k, JSON.stringify(v));
export const clearAll = (prefix = 'fiq_') => { (kv.keys?.() ?? []).filter((k) => k.startsWith(prefix)).forEach((k) => kv.removeItem(k)); };
