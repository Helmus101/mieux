// Service worker: the app opens instantly from the cache and updates itself in the background. API calls always go to the network.
// Bump C on every change to this file: the old cache is dropped on activation.
const C = 'mieux-shell-v5';
const SHELL = ['/app', '/favicon.svg', '/icon-180.png', '/icon-192.png', '/logo.svg', '/manifest.webmanifest'];

// Shown only when a page is requested while offline and nothing is cached yet (first visit without network).
const OFFLINE_PAGE = `<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>Mieux — hors ligne</title>
<style>body{margin:0;min-height:100dvh;display:flex;align-items:center;justify-content:center;background:#fff;color:#14201A;font:16px/1.5 -apple-system,system-ui,sans-serif;text-align:center;padding:24px}
@media(prefers-color-scheme:dark){body{background:#0D1210;color:#F2F5F3}}b{font-size:28px;letter-spacing:-1px}i{font-style:normal;color:#F26B3A}p{color:#5A6660;max-width:32ch}
button{font:inherit;font-weight:600;padding:14px 22px;border-radius:8px;border:0;background:#1F4D3A;color:#fff;min-height:48px}</style></head>
<body><div><b>mieux<i>.</i></b><p>Pas de connexion pour l'instant. L'application s'ouvrira dès que le réseau revient.</p><button onclick="location.reload()">Réessayer</button></div></body></html>`;

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(C).then((c) => Promise.allSettled(SHELL.map((u) => c.add(u)))));  // a missing icon must not block the install
  self.skipWaiting();
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== C).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
// The page asks for the version to show "new version available" at the right time.
self.addEventListener('message', (e) => { if (e.data === 'SKIP_WAITING') self.skipWaiting(); });

// Only real files are kept: after a deploy a missing script can come back as the HTML page, and caching that would freeze the app.
const refresh = (req) => fetch(req).then((r) => {
  const html = (r.headers.get('content-type') || '').includes('text/html');
  const isPage = req.mode === 'navigate' || new URL(req.url).pathname === '/app';
  if (r.ok && (isPage || !html)) { const cp = r.clone(); caches.open(C).then((c) => c.put(req, cp)); }
  return r;
});
const offline = () => new Response(OFFLINE_PAGE, { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' } });

self.addEventListener('fetch', (e) => {
  const req = e.request, u = new URL(req.url);
  if (req.method !== 'GET' || u.origin !== location.origin || u.pathname.startsWith('/v1')) return;
  if (req.mode === 'navigate') {  // the shell: the fresh copy when the network answers quickly (so a new version shows at once), the saved copy when it is slow or offline
    e.respondWith(caches.match('/app').then((m) => {
      const net = refresh(new Request('/app'));
      if (!m) return net.catch(offline);
      return Promise.race([net.catch(() => m), new Promise((ok) => setTimeout(() => ok(m), 1200))]);
    }));
    return;
  }
  if (u.pathname.startsWith('/assets/')) {  // hashed files never change: cache first
    e.respondWith(caches.match(req).then((m) => m || refresh(req)));
    return;
  }
  e.respondWith(caches.match(req).then((m) => { const net = refresh(req).catch(() => m || Response.error()); return m || net; }));
});
