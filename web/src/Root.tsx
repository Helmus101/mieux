import { lazy, Suspense, useEffect, useState } from 'react';
import { APP_PATH, wantsLanding } from './install';
import { trackVisit } from './usage';

// Loaded separately on purpose: the landing page must not download the app's router, API client and stores.
const App = lazy(() => import('./App'));
const Landing = lazy(() => import('./screens/Landing'));
const Usage = lazy(() => import('./screens/Usage'));

/** `/stats`: the plain count of people using Mieux, openable by anyone with the link. */
const atStats = () => window.location.pathname.replace(/\/+$/, '') === '/stats';

/** Landing page at `/` for computers and iPads; everywhere else goes straight to the app at /app. */
function start(): boolean {
  const landing = wantsLanding();
  // Root reached without the landing page (?app, or a phone): go to the app and drop the marker from the URL.
  if (!landing && window.location.pathname === '/') {
    const { search, hash } = window.location;
    const q = new URLSearchParams(search); q.delete('app');
    const rest = q.toString();
    window.history.replaceState(null, '', APP_PATH + (rest ? '?' + rest : '') + hash);
  }
  return landing;
}

export default function Root() {
  const [stats, setStats] = useState(atStats);
  const [landing, setLanding] = useState(start);
  // One anonymous count per person per day for the landing page and for the app; the server does the deduplicating.
  // The stats page is not counted: it is the owner reading the numbers, not a new person.
  useEffect(() => { if (!stats) trackVisit(landing ? 'landing' : 'app'); }, [landing, stats]);
  // Back from /app must show the landing page again, not leave the app sitting on the root URL.
  useEffect(() => {
    const sync = () => { setStats(atStats()); setLanding(wantsLanding()); };
    window.addEventListener('popstate', sync);
    return () => window.removeEventListener('popstate', sync);
  }, []);
  if (stats) return (
    <Suspense fallback={null}>
      <Usage onBack={() => { window.history.pushState(null, '', '/'); setStats(false); setLanding(wantsLanding()); }} />
    </Suspense>
  );
  if (landing) return (
    <Suspense fallback={null}>
      <Landing onEnter={() => { window.history.pushState(null, '', APP_PATH); setLanding(false); }} />
    </Suspense>
  );
  return <Suspense fallback={null}><App /></Suspense>;
}
