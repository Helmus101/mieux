// Registers the service worker and tells the page when a new version has taken over, so it can offer one tap to refresh
// instead of failing later on a script that the new deploy no longer serves.
export const SW_UPDATED = 'mieux:sw-updated';

export function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) return;
  const secure = location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  if (!secure) return;
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').then((reg) => {
      // Check for a new build whenever the app comes back to the foreground (installed apps stay open for days).
      document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') reg.update().catch(() => undefined); });
    }).catch(() => undefined);
    // A controller change with a controller already present means a new version has activated under a running page.
    let had = !!navigator.serviceWorker.controller;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (had) window.dispatchEvent(new Event(SW_UPDATED));
      had = true;
    });
  });
}
