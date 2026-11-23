// One canonical address per page: the app is a single HTML file served for every route, so the link is kept in step with the route.
const SITE = ((import.meta as unknown as { env?: Record<string, string> }).env?.VITE_SITE_URL || 'https://mieuxmanger.vercel.app').replace(/\/$/, '');
export function setCanonical(pathname: string) {
  try {
    let l = document.querySelector<HTMLLinkElement>('link[rel="canonical"]');
    if (!l) { l = document.createElement('link'); l.rel = 'canonical'; document.head.appendChild(l); }
    const p = pathname.replace(/\/+$/, '');
    l.href = SITE + (p || '/');
  } catch { /* no document (tests) */ }
}

/** Keeps the canonical link in step with the address for the whole life of the page, whichever router moved it (pushState, replaceState, back). */
export function watchCanonical() {
  const sync = () => setCanonical(window.location.pathname);
  for (const k of ['pushState', 'replaceState'] as const) {
    const orig = history[k];
    history[k] = function (this: History, ...a: Parameters<History['pushState']>) { const r = orig.apply(this, a); sync(); return r; };
  }
  window.addEventListener('popstate', sync);
  sync();
}
