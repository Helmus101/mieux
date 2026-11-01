// Anonymous usage ping: the server counts one visit per person, per surface, per day.
// Nothing is stored in the browser (no cookie, no id) and failures never affect the page.
import { getApiBase } from './config';

export type Surface = 'landing' | 'app';

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
