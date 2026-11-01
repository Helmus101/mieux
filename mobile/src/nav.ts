// Navigation seam (mirrors web/src/nav.ts) on top of expo-router.
import { useRouter } from 'expo-router';
export const routes = {
  home: '/', scan: '/scan', compare: '/compare', purchases: '/purchases', profile: '/profile', receipt: '/receipt', history: '/history',
  product: (code: string) => `/product/${code}`, alternatives: (code: string) => `/alternatives/${code}`,
};
export function useNav() { const r = useRouter(); return { go: (p: string) => r.push(p as never), back: () => r.back() }; }
