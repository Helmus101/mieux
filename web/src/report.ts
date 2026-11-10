// Uncaught errors are sent to the API (one line in the server logs, nothing stored) so a broken release is noticed without a third-party tracker.
// Nothing personal is sent: message, stack, path and app version only.
import { getApiBase } from '@shared/config';

export const APP_VERSION: string = typeof __APP_VERSION__ === 'string' ? __APP_VERSION__ : 'dev';

type Kind = 'error' | 'promise' | 'chunk' | 'boundary';
const sent = new Set<string>();
let budget = 5;  // per page load: a render loop must not flood the server

export function report(kind: Kind, err: unknown) {
  try {
    const e = err as { message?: string; stack?: string } | null;
    const message = String(e?.message ?? err ?? 'unknown').slice(0, 600);
    if (!message || /ResizeObserver loop|Script error\.?$/.test(message)) return;  // browser noise, not app bugs
    const key = kind + message;
    if (sent.has(key) || budget-- <= 0) return;
    sent.add(key);
    const body = JSON.stringify({ kind, message, stack: e?.stack?.slice(0, 4000), url: location.pathname.slice(0, 400), version: APP_VERSION });
    const url = getApiBase().replace(/\/+$/, '') + '/client-errors';
    if (!(navigator.sendBeacon && navigator.sendBeacon(url, new Blob([body], { type: 'application/json' }))))
      void fetch(url, { method: 'POST', body, headers: { 'Content-Type': 'application/json' }, keepalive: true }).catch(() => undefined);
  } catch { /* reporting must never throw */ }
}

/** Call once at start-up. */
export function installErrorReporting() {
  window.addEventListener('error', (ev) => report('error', ev.error ?? ev.message));
  window.addEventListener('unhandledrejection', (ev) => report('promise', ev.reason));
}
