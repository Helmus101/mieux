import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { lazy, Suspense, useEffect } from 'react';
import { api } from '@shared/api/client';
import { t, setLocale } from '@shared/i18n';
import { useProfile, apiPrefs } from '@shared/stores';
import { Skeleton, Screen, haptic } from './ui';
import { routes, useNav } from './nav';
import InstallPrompt from './InstallPrompt';
import { APP_PATH } from './install';
import './index.css';

const Onboarding = lazy(() => import('./screens/Onboarding'));
const Home = lazy(() => import('./screens/Home'));
const Scan = lazy(() => import('./screens/Scan'));
const Product = lazy(() => import('./screens/Product'));
const Alternatives = lazy(() => import('./screens/Alternatives'));
const Compare = lazy(() => import('./screens/Compare'));
const Profile = lazy(() => import('./screens/Profile'));
const History = lazy(() => import('./screens/History'));
const Blog = lazy(() => import('./screens/Blog'));
const BlogPost = lazy(() => import('./screens/BlogPost'));

const I = {
  home: <path d="M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10" />,
  compare: <path d="M8 3L4 7l4 4M4 7h13M16 21l4-4-4-4M20 17H7" />,
  scan: <path d="M4 8V5a1 1 0 011-1h3M16 4h3a1 1 0 011 1v3M20 16v3a1 1 0 01-1 1h-3M8 20H5a1 1 0 01-1-1v-3M7 12h10" />,
  profile: <path d="M12 12a4 4 0 100-8 4 4 0 000 8zM4 21a8 8 0 0116 0" />,
};

/** The tab this route belongs to; the app lives under /app, so strip that prefix first. */
const sectionOf = (pathname: string) => pathname.replace(/^\/app\/?/, '').split('/')[0] || 'home';

function TabBar() {
  const { go } = useNav();
  const cur = sectionOf(useLocation().pathname);
  const items: [keyof typeof I, string][] = [['home', routes.home], ['scan', routes.scan], ['profile', routes.profile]];
  return (
    <nav className="tabbar"><div className="in">
      {items.map(([k, path]) => (
        <button key={k} className={'tab' + (k === 'scan' ? ' fab' : '') + (cur === k || (k === 'scan' && cur === 'product') ? ' on' : '')} onClick={() => { haptic(k === 'scan' ? 'tap' : 'select'); go(path); }}>
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
  // Set locale on app load
  useEffect(() => { if (language) setLocale(language); }, [language]);
  // Keep the (local) server in sync so fit checks and price-aware ranking use the saved profile.
  useEffect(() => { if (onboarded) api.updatePreferences(apiPrefs({ priorities, diet, allergens }) as never).catch(() => undefined); }, [onboarded, priorities, diet, allergens]);
  if (!onboarded) return <Suspense fallback={null}><Onboarding /></Suspense>;
  return (
    <div className="app">
      <Suspense fallback={<Screen><Skeleton h={40} w="60%" /><Skeleton h={120} /><Skeleton h={120} /></Screen>}>
        <Routes>
          <Route index element={<Home />} />
          <Route path="scan" element={<Scan />} />
          <Route path="product/:barcode" element={<Product />} />
          <Route path="alternatives/:barcode" element={<Alternatives />} />
          <Route path="compare" element={<Compare />} />
          <Route path="profile" element={<Profile />} />
          <Route path="history" element={<History />} />
          <Route path="*" element={<Navigate to={routes.home} replace />} />
        </Routes>
      </Suspense>
      <InstallPrompt hidden={sectionOf(pathname) === 'scan'} />
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
