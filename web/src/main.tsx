import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { setApiBase } from '@shared/config';
import './index.css';

const envBase = (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_BASE_URL;
if (envBase) setApiBase(envBase);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

if ('serviceWorker' in navigator && location.protocol !== 'http:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
  window.addEventListener('load', () => { navigator.serviceWorker?.register('/sw.js').catch(() => undefined); });
}
