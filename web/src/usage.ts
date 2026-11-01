// Anonymous usage ping: the server counts one visit per person, per surface, per day.
// Nothing is stored in the browser (no cookie, no id) and failures never affect the page.
import { getApiBase } from './config';

export type Surface = 'landing' | 'app';

export interface UsageStats {
  since: string;
  days: number;
  visitors: number;
  app_visitors: number;
  views: number;
  landing_views: number;
  app_opens: number;
  today: { day: string; visitors: number; views: number; landing_views: number; app_opens: number };
  daily: { day: string; visitors: number; views: number; landing_views: number; app_opens: number }[];
  note: string;
}

/** Totals only: the server never returns a name or an address here. */
export async function fetchUsageStats(days = 30): Promise<UsageStats> {
  const r = await fetch(`${getApiBase()}/usage/stats?days=${days}`);
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}

export function trackVisit(surface: Surface): void {
  try {
    void fetch(`${getApiBase()}/usage/visit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ surface }),
      keepalive: true,
    }).catch(() => undefined);
  } catch { /* offline or blocked */ }
}
