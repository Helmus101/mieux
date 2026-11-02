import React from 'react';
import ReactDOM from 'react-dom/client';
import { Analytics } from '@vercel/analytics/react';
import Root from './Root';
import { setApiBase, setStrict } from '@shared/config';
// index.css is imported by App: the landing page has its own stylesheet and no app CSS.

const envBase = (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_BASE_URL;
if (envBase) setApiBase(envBase);

// Always use strict mode (Yuka-like additive evaluation)
setStrict(true);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Root />
    <Analytics />
  </React.StrictMode>,
);

if ('serviceWorker' in navigator && location.protocol !== 'http:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
  window.addEventListener('load', () => { navigator.serviceWorker?.register('/sw.js').catch(() => undefined); });
}
