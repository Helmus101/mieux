import { useProfile } from '@shared/stores';

/* Stale-while-revalidate: show the last answer for a key at once, then replace it with the fresh one.
 * Kept in localStorage so a recently opened product is on screen the moment the app reopens (and opens offline too); the
 * oldest entries are dropped first so the cache can never fill the browser's storage. */
const PREFIX = 'mx_swr_';
const MAX_ENTRIES = 30;
const MAX_ENTRY_CHARS = 150_000;   // a huge answer would crowd out the person's own history in the 5 MB the browser allows
const store = (): Storage | null => { try { return localStorage; } catch { return null; } };

export function readCache<T>(key: string, maxAgeMs = 30 * 60_000): T | null {
  try {
    const raw = store()?.getItem(PREFIX + key);
    if (!raw) return null;
    const { at, v } = JSON.parse(raw);
    return Date.now() - at < maxAgeMs ? (v as T) : null;
  } catch { return null; }
}

/** Drops the oldest cache entries until at most `keep` remain. */
function prune(s: Storage, keep: number) {
  const rows: { k: string; at: number }[] = [];
  for (let i = 0; i < s.length; i++) {
    const k = s.key(i);
    if (!k || !k.startsWith(PREFIX)) continue;
    let at = 0;
    try { at = JSON.parse(s.getItem(k) || '{}').at || 0; } catch { /* unreadable entry: oldest */ }
    rows.push({ k, at });
  }
  rows.sort((a, b) => a.at - b.at).slice(0, Math.max(0, rows.length - keep)).forEach((r) => s.removeItem(r.k));
}

export function writeCache(key: string, v: unknown) {
  const s = store();
  if (!s) return;
  const val = JSON.stringify({ at: Date.now(), v });
  if (val.length > MAX_ENTRY_CHARS) return;
  try { s.setItem(PREFIX + key, val); } catch {
    // Storage full: make room by dropping the oldest half, then try once more; no cache is better than an error.
    try { prune(s, Math.floor(MAX_ENTRIES / 2)); s.setItem(PREFIX + key, val); } catch { /* give up quietly */ }
  }
  try { if (Math.random() < 0.2) prune(s, MAX_ENTRIES); } catch { /* ignore */ }
}

/** How long a product page may be shown from the cache before the fresh answer replaces it (it is always refetched). */
export const PRODUCT_CACHE_MS = 24 * 60 * 60_000;

/** Product-page payload keyed by everything that changes the answer, so the scan peek's fetch is reused on open. */
export const prodKey = (barcode: string, approximate: boolean, strict: boolean) => {
  // The restriction check (allergens, diet) is part of the answer: a changed profile must never be shown yesterday's "suitable".
  const p = useProfile.getState();
  return `prod:${barcode}:${approximate ? 1 : 0}:${strict ? 1 : 0}:${p.diet ?? 'omnivore'}:${[...(p.allergens ?? [])].sort().join('+')}`;
};
