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
/** Runs a navigation inside a view transition when the browser supports it (a short cross-fade), otherwise just navigates. */
const withTransition = (f: () => void) => {
  const d = document as Document & { startViewTransition?: (cb: () => void) => unknown };
  if (d.startViewTransition && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) d.startViewTransition(f); else f();
};
export function useNav() { const n = useNavigate(); return { go: (p: string, state?: unknown) => withTransition(() => n(p, { state })), back: () => withTransition(() => n(-1)) }; }
