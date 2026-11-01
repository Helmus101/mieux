// Navigation seam: screens call useNav(); in Expo replace with expo-router / React Navigation equivalents.
import { useNavigate } from 'react-router-dom';
export const routes = {
  home: '/', scan: '/scan', compare: '/compare', profile: '/profile',
  product: (code: string) => `/product/${code}`, alternatives: (code: string) => `/alternatives/${code}`,
  history: '/history',
};
export function useNav() { const n = useNavigate(); return { go: (p: string, state?: unknown) => n(p, { state }), back: () => n(-1) }; }
