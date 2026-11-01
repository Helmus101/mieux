import { lazy, Suspense, useState } from 'react';
import { APP_PATH, enterApp, wantsLanding } from './install';

// Loaded separately on purpose: the landing page must not download the app's router, API client and stores.
const App = lazy(() => import('./App'));
const Landing = lazy(() => import('./screens/Landing'));

/** Landing page at `/` for computers and iPads; everywhere else goes straight to the app at /app. */
function start(): boolean {
  if (wantsLanding()) return true;
  const { pathname, search, hash } = window.location;
  if (pathname === '/') {
    const q = new URLSearchParams(search); q.delete('app');
    const rest = q.toString();
    window.history.replaceState(null, '', APP_PATH + (rest ? '?' + rest : '') + hash);
  }
  return false;
}

export default function Root() {
  const [landing, setLanding] = useState(start);
  if (landing) return (
    <Suspense fallback={null}>
      <Landing onEnter={() => { enterApp(); window.history.pushState(null, '', APP_PATH); setLanding(false); }} />
    </Suspense>
  );
  return <Suspense fallback={null}><App /></Suspense>;
}
