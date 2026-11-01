// Anonymous usage ping: the server counts one visit per person, per surface, per day.
// Nothing is stored in the browser (no cookie, no id) and failures never affect the page.
import { load, save } from '@shared/storage';
import { getApiBase } from './config';

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
function sessionId(): string | null {
  try {
    let id = load<string | null>('fiq_session_id', null);
    if (!id) { id = 'anon-' + Math.random().toString(36).slice(2) + Date.now().toString(36); save('fiq_session_id', id); }
    return id;
  } catch { return null; }
}

export function trackVisit(surface: Surface): void {
  try {
    const sid = sessionId();
    void fetch(`${getApiBase()}/usage/visit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(sid ? { 'X-Session-Id': sid } : {}) },
      body: JSON.stringify({ surface }),
      keepalive: true,
    }).catch(() => undefined);
  } catch { /* offline or blocked */ }
}
