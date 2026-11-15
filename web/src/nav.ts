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
const TABS = [routes.list, routes.scan, routes.profile];
export function useNav() {
  const n = useNavigate();
  return {
    go: (p: string, state?: unknown) => withTransition(() => n(p, { state }), TABS.includes(p) ? 'tab' : 'push'),
    back: () => withTransition(() => n(-1), 'pop'),
  };
}
