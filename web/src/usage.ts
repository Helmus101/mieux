// Anonymous usage ping: the server counts one visit per person, per surface, per day.
// One first-party cookie (mx_vid, random, 13 months, used only for this count) tells distinct visitors apart; failures never affect the page.
import { load, save } from '@shared/storage';
import { getApiBase } from '@shared/config';

export type Surface = 'landing' | 'app';

export interface UsageStats {
  since: string;
  days: number;
  people: number;
  people_today: number;
  returning: number;
  visitors: number;
  app_visitors: number;
  views: number;
  landing_views: number;
  app_opens: number;
  today: { day: string; visitors: number; views: number; landing_views: number; app_opens: number };
  daily: { day: string; visitors: number; people: number; views: number; landing_views: number; app_opens: number }[];
  note: string;
}

/** Totals only: the server never returns a name or an address here. */
export async function fetchUsageStats(days = 30): Promise<UsageStats> {
  const r = await fetch(`${getApiBase()}/usage/stats?days=${days}`);
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

/** The same anonymous id the API client keeps in this browser (it stores scans under it). Sending it lets the server
 *  count distinct people across days; it is hashed there and never stored as is. No cookie is created. */
const COOKIE = 'mx_vid';
/** Audience measurement only: first-party, random, no link to a person, 13 months at most (CNIL exemption). */
function visitorCookie(): string | null {
  try {
    const m = document.cookie.match(new RegExp('(?:^|; )' + COOKIE + '=([^;]+)'));
    let id = m ? decodeURIComponent(m[1]) : null;
    if (!id) id = 'v-' + (crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36));
    document.cookie = `${COOKIE}=${encodeURIComponent(id)}; Max-Age=${60 * 60 * 24 * 395}; Path=/; SameSite=Lax${location.protocol === 'https:' ? '; Secure' : ''}`;
    return id;
  } catch { return null; }
}
export const countingOff = () => { try { return localStorage.getItem('mx_no_count') === '1' || navigator.doNotTrack === '1' || (navigator as unknown as { globalPrivacyControl?: boolean }).globalPrivacyControl === true; } catch { return false; } };
export function setCounting(on: boolean) {
  try {
    if (on) localStorage.removeItem('mx_no_count'); else { localStorage.setItem('mx_no_count', '1'); document.cookie = `${COOKIE}=; Max-Age=0; Path=/`; }
  } catch { /* storage unavailable */ }
}
function sessionId(): string | null {
  if (countingOff()) return null;
  const c = visitorCookie();
  if (c) return c;
  try {
    let id = load<string | null>('fiq_session_id', null);
    if (!id) { id = 'anon-' + Math.random().toString(36).slice(2) + Date.now().toString(36); save('fiq_session_id', id); }
    return id;
  } catch { return null; }
}

export function trackVisit(surface: Surface): void {
  try {
    if (countingOff()) return;
    const sid = sessionId();
    void fetch(`${getApiBase()}/usage/visit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(sid ? { 'X-Session-Id': sid } : {}) },
      body: JSON.stringify({ surface }),
      keepalive: true,
    }).catch(() => undefined);
  } catch { /* offline or blocked */ }
}
