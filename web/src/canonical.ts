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
