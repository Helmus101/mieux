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

// Account-scoped storage: if a user ID is provided, keys are prefixed with it
let currentAccountId: string | null = null;
export const setAccountId = (uid: string | null) => { currentAccountId = uid; };
export const getAccountId = () => currentAccountId;

/** Prefixes the key with the account ID if one is set, for account-scoped local storage */
const scopedKey = (k: string): string => currentAccountId ? `${k}_${currentAccountId}` : k;

/** Reads JSON. Tolerates a legacy raw string value when the default is a string/null (older versions stored the session id unquoted). */
export const load = <T,>(k: string, d: T): T => {
  const raw = kv.getItem(scopedKey(k));
  if (raw == null) return d;
  try { return JSON.parse(raw) as T; } catch { return (typeof d === 'string' || d === null ? (raw as unknown as T) : d); }
};
export const save = (k: string, v: unknown) => kv.setItem(scopedKey(k), JSON.stringify(v));
export const clearAll = (prefix = 'fiq_') => { (kv.keys?.() ?? []).filter((k) => k.startsWith(prefix)).forEach((k) => kv.removeItem(k)); };
