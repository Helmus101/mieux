// Service worker: the app opens instantly from the cache and updates itself in the background. API calls always go to the network.
const C = 'mieux-shell-v5', IMG = 'mieux-img-v1';
self.addEventListener('install', e => { e.waitUntil(caches.open(C).then(c => c.addAll(['/app', '/favicon.svg', '/icon-180.png']))); self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== C && k !== IMG).map(k => caches.delete(k))))); self.clients.claim(); });
// Only real files are kept: after a deploy a missing script can come back as the HTML page, and caching that would freeze the app.
const refresh = (req) => fetch(req).then(r => { const html = (r.headers.get('content-type') || '').includes('text/html'); const isPage = req.mode === 'navigate' || new URL(req.url).pathname === '/app'; if (r.ok && (isPage || !html)) { const cp = r.clone(); caches.open(C).then(c => c.put(req, cp)); } return r; });
self.addEventListener('fetch', e => {
  const req = e.request, u = new URL(req.url);
  if (req.method === 'GET' && req.destination === 'image' && u.hostname.endsWith('openfoodfacts.org')) {   // product photos: shown from the saved copy at once, saved on first sight (at most 400 kept)
    e.respondWith(caches.open(IMG).then(c => c.match(req).then(m => m || fetch(req).then(r => { if (r.ok || r.type === 'opaque') { c.put(req, r.clone()); c.keys().then(k => { if (k.length > 400) c.delete(k[0]); }); } return r; }))));
    return;
  }
  if (req.method !== 'GET' || u.origin !== location.origin || u.pathname.startsWith('/v1')) return;
  if (req.mode === 'navigate') {  // the shell: the fresh copy when the network answers quickly (so a new version shows at once), the saved copy when it is slow or offline
    e.respondWith(caches.match('/app').then(m => {
      const net = refresh(new Request('/app'));
      if (!m) return net.catch(() => Response.error());
      return Promise.race([net.catch(() => m), new Promise(ok => setTimeout(() => ok(m), 1200))]);
    }));
    return;
  }
  if (u.pathname.startsWith('/assets/')) {  // hashed files never change: cache first
    e.respondWith(caches.match(req).then(m => m || refresh(req)));
    return;
  }
  e.respondWith(caches.match(req).then(m => { const net = refresh(req).catch(() => m || Response.error()); return m || net; }));
});
