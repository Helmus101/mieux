/** Deletes everything this app keeps on the device: settings, history, saved products, the product and photo caches,
 *  the service worker and its caches. After this the app starts as a fresh install. */
export async function wipeLocalData(): Promise<void> {
  try { localStorage.clear(); } catch { /* storage unavailable */ }
  try { document.cookie = 'mx_vid=; Max-Age=0; Path=/'; } catch { /* cookies unavailable */ }
  try { sessionStorage.clear(); } catch { /* storage unavailable */ }
  try { const keys = await caches.keys(); await Promise.all(keys.map((k) => caches.delete(k))); } catch { /* no Cache API */ }
  try { const regs = (await navigator.serviceWorker?.getRegistrations()) ?? []; await Promise.all(regs.map((r) => r.unregister())); } catch { /* no service worker */ }
  try {
    const dbs = (await (indexedDB as unknown as { databases?: () => Promise<{ name?: string }[]> }).databases?.()) ?? [];
    await Promise.all(dbs.map((d) => new Promise<void>((ok) => { if (!d.name) return ok(); const r = indexedDB.deleteDatabase(d.name); r.onsuccess = r.onerror = r.onblocked = () => ok(); })));
  } catch { /* no IndexedDB listing */ }
}
