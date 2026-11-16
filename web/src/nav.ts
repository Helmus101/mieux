// Navigation seam: screens call useNav(); in Expo replace with expo-router / React Navigation equivalents.
// The app lives under /app, so the root is free for the landing page.
import { useNavigate } from 'react-router-dom';
export const routes = {
  home: '/app/scan', scan: '/app/scan', compare: '/app/compare', profile: '/app/profile',
  product: (code: string) => `/app/product/${code}`, alternatives: (code: string) => `/app/alternatives/${code}`,
  history: '/app/history', list: '/app/list',
  blog: '/blog',
  blogPost: (slug: string) => `/blog/${slug}`,
};
/** Runs a navigation inside a view transition when the browser supports it, otherwise just navigates.
 *  `dir` picks the motion like iOS: "push" slides in from the right, "pop" slides back out, "tab" is a plain cross-fade. */
const withTransition = (f: () => void, dir: 'push' | 'pop' | 'tab') => {
  const d = document as Document & { startViewTransition?: (cb: () => void) => { finished: Promise<unknown> } };
  if (!d.startViewTransition || window.matchMedia('(prefers-reduced-motion: reduce)').matches) { f(); return; }
  const root = document.documentElement;
  root.dataset.nav = dir;
  const clear = () => { delete root.dataset.nav; };
  d.startViewTransition(f).finished.then(clear, clear);
};
const TABS = [routes.list, routes.scan, routes.profile, routes.compare];
/** Where each top-level tab was scrolled to when the user left it, so coming back lands on the same spot like a native tab bar. */
const tabScroll = new Map<string, number>();
export const savedTabScroll = (path: string) => (TABS.includes(path) ? tabScroll.get(path) ?? 0 : 0);
const rememberScroll = () => { const p = window.location.pathname; if (TABS.includes(p)) tabScroll.set(p, window.scrollY); };
export function useNav() {
  const n = useNavigate();
  return {
    go: (p: string, state?: unknown) => { rememberScroll(); withTransition(() => n(p, { state }), TABS.includes(p) ? 'tab' : 'push'); },
    back: () => { rememberScroll(); withTransition(() => n(-1), 'pop'); },
  };
}
