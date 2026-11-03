// Navigation seam: screens call useNav(); in Expo replace with expo-router / React Navigation equivalents.
// The app lives under /app, so the root is free for the landing page.
import { useNavigate } from 'react-router-dom';
export const routes = {
  home: '/app', scan: '/app/scan', compare: '/app/compare', profile: '/app/profile',
  product: (code: string) => `/app/product/${code}`, alternatives: (code: string) => `/app/alternatives/${code}`,
  history: '/app/history', admin: '/app/admin',
  blog: '/blog',
  blogPost: (slug: string) => `/blog/${slug}`,
};
export function useNav() { const n = useNavigate(); return { go: (p: string, state?: unknown) => n(p, { state }), back: () => n(-1) }; }
