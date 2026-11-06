import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { lazy as reactLazy, Suspense, useEffect, type ComponentType } from 'react';
import { api } from '@shared/api/client';
import { t, setLocale } from '@shared/i18n';
import { useProfile, apiPrefs } from '@shared/stores';
import { Loader, Screen, haptic } from './ui';
import { routes, useNav } from './nav';
import ErrorBoundary from './ErrorBoundary';
import { ACCOUNT_REQUIRED, accountEnabled, initAccount, useAccount } from './account';
import { APP_PATH } from './install';
import './index.css';

// A screen's script downloads the first time it is opened; on a weak connection that can fail once, so try again before giving up.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Screen = { default: ComponentType<any> };
const lazy = (load: () => Promise<Screen>) => reactLazy(() => load().catch(() => new Promise<void>((ok) => setTimeout(ok, 600)).then(load)));

const Onboarding = lazy(() => import('./screens/Onboarding'));
const Scan = lazy(() => import('./screens/Scan'));
const Product = lazy(() => import('./screens/Product'));
const Alternatives = lazy(() => import('./screens/Alternatives'));
const Compare = lazy(() => import('./screens/Compare'));
const Profile = lazy(() => import('./screens/Profile'));
const History = lazy(() => import('./screens/History'));
const List = lazy(() => import('./screens/List'));
const Blog = lazy(() => import('./screens/Blog'));
const BlogPost = lazy(() => import('./screens/BlogPost'));

const I = {
  home: <path d="M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10" />,
  compare: <path d="M8 3L4 7l4 4M4 7h13M16 21l4-4-4-4M20 17H7" />,
  list: <path d="M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01" />,
  scan: <path d="M4 8V5a1 1 0 011-1h3M16 4h3a1 1 0 011 1v3M20 16v3a1 1 0 01-1 1h-3M8 20H5a1 1 0 01-1-1v-3M7 12h10" />,
  profile: <path d="M12 12a4 4 0 100-8 4 4 0 000 8zM4 21a8 8 0 0116 0" />,
};

/** The tab this route belongs to; the app lives under /app, so strip that prefix first. */
const sectionOf = (pathname: string) => pathname.replace(/^\/app\/?/, '').split('/')[0] || 'home';

function TabBar() {
  const { go } = useNav();
  const cur = sectionOf(useLocation().pathname);
  const items: [keyof typeof I, string][] = [['scan', routes.scan], ['list', routes.list], ['profile', routes.profile]];
  return (
    <nav className="tabbar"><div className="in">
      {items.map(([k, path]) => (
        <button key={k} className={'tab' + (k === 'scan' ? ' fab' : '') + (cur === k || (k === 'scan' && (cur === 'product' || cur === 'alternatives')) || (k === 'list' && (cur === 'compare' || cur === 'history')) ? ' on' : '')} onClick={() => { haptic(k === 'scan' ? 'tap' : 'select'); go(path); }}>
          {k === 'scan' ? <span className="disc"><svg viewBox="0 0 24 24">{I[k]}</svg></span> : <svg viewBox="0 0 24 24">{I[k]}</svg>}
          <span>{t('tabs.' + k)}</span>
        </button>
      ))}
    </div></nav>
  );
}

function Shell() {
  const profile = useProfile();
  const { pathname } = useLocation();
  const { onboarded, priorities, diet, allergens, language } = profile;
  useEffect(() => { initAccount(); }, []);
  // Set locale on app load
  useEffect(() => { if (language) setLocale(language); }, [language]);
  // Keep the (local) server in sync so fit checks and price-aware ranking use the saved profile.
  useEffect(() => { api.setPrefs(apiPrefs({ priorities, diet, allergens })); if (onboarded) api.updatePreferences(apiPrefs({ priorities, diet, allergens }) as never).catch(() => undefined); }, [onboarded, priorities, diet, allergens]);
  const signedIn = useAccount((a) => a.email), accountReady = useAccount((a) => a.ready);
  if (accountEnabled && ACCOUNT_REQUIRED && !accountReady) return <Screen><Loader /></Screen>;
  // The add-to-home-screen banner shows from the very first screen (sign-in, onboarding), not only inside the app.
  if (accountEnabled && ACCOUNT_REQUIRED && !signedIn) return <><Suspense fallback={null}><Onboarding gate /></Suspense></>;  // an account is required to use the app
  if (!onboarded) return <><Suspense fallback={null}><Onboarding /></Suspense></>;
  return (
    <div className="app">
      <ErrorBoundary resetKey={pathname}><Suspense fallback={<Screen><Loader /></Screen>}>
        <Routes>
          <Route index element={<Navigate to="scan" replace />} />
          <Route path="scan" element={<Scan />} />
          <Route path="product/:barcode" element={<Product />} />
          <Route path="alternatives/:barcode" element={<Alternatives />} />
          <Route path="compare" element={<Compare />} />
          <Route path="profile" element={<Profile />} />
          <Route path="history" element={<History />} />
          <Route path="list" element={<List />} />
          <Route path="*" element={<Navigate to={routes.home} replace />} />
        </Routes>
      </Suspense></ErrorBoundary>
      <TabBar />
    </div>
  );
}

/** Links from before the app moved (/scan, /product/…, or a bare /): keep them working. */
function ToApp() {
  const { pathname, search, hash } = useLocation();
  const to = pathname === '/' ? APP_PATH : APP_PATH + pathname;
  return <Navigate to={{ pathname: to, search, hash }} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path={APP_PATH + '/*'} element={<Shell />} />
        <Route path="/blog" element={<Suspense fallback={null}><Blog /></Suspense>} />
        <Route path="/blog/:slug" element={<Suspense fallback={null}><BlogPost /></Suspense>} />
        <Route path="*" element={<ToApp />} />
      </Routes>
    </BrowserRouter>
  );
}
