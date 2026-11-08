/* Stale-while-revalidate: show the last answer for a key at once, then replace it with the fresh one. Kept in sessionStorage for the tab. */
const PREFIX = 'mx_swr_';
export function readCache<T>(key: string, maxAgeMs = 30 * 60_000): T | null {
  try {
    const raw = sessionStorage.getItem(PREFIX + key);
    if (!raw) return null;
    const { at, v } = JSON.parse(raw);
    return Date.now() - at < maxAgeMs ? (v as T) : null;
  } catch { return null; }
}
export function writeCache(key: string, v: unknown) {
  try { sessionStorage.setItem(PREFIX + key, JSON.stringify({ at: Date.now(), v })); } catch { /* storage full or unavailable: just no cache */ }
}
