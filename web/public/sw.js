// Service worker: the app opens instantly from the cache and updates itself in the background. API calls always go to the network.
const C = 'mieux-shell-v2';
self.addEventListener('install', e => { e.waitUntil(caches.open(C).then(c => c.addAll(['/app', '/favicon.svg', '/icon-180.png']))); self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k))))); self.clients.claim(); });
const refresh = (req) => fetch(req).then(r => { if (r.ok) { const cp = r.clone(); caches.open(C).then(c => c.put(req, cp)); } return r; });
self.addEventListener('fetch', e => {
  const req = e.request, u = new URL(req.url);
  if (req.method !== 'GET' || u.origin !== location.origin || u.pathname.startsWith('/v1')) return;
  if (req.mode === 'navigate') {  // the shell: show the saved copy at once, fetch a fresh one for next time
    e.respondWith(caches.match('/app').then(m => { const net = refresh(new Request('/app')).catch(() => m); return m || net; }));
    return;
  }
  if (u.pathname.startsWith('/assets/')) {  // hashed files never change: cache first
    e.respondWith(caches.match(req).then(m => m || refresh(req)));
    return;
  }
  e.respondWith(caches.match(req).then(m => { const net = refresh(req).catch(() => m); return m || net; }));
});
