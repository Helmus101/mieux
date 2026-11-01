import { fr } from './fr';

// French is the default (and currently only) UI language; add another dictionary and register it here.
const dicts: Record<string, any> = { fr };
let locale = 'fr';
export const getLocale = () => locale;
export const setLocale = (l: string) => { if (dicts[l]) locale = l; };

/** t('home.title') or t('home.boughtN', { n: 3 }) */
export function t(path: string, vars?: Record<string, string | number>): string {
  const d = dicts[locale] ?? fr;
  const v = path.split('.').reduce((o: any, k) => (o == null ? o : o[k]), d) ?? path.split('.').reduce((o: any, k) => (o == null ? o : o[k]), fr);
  if (typeof v !== 'string') return path;
  return vars ? v.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? '')) : v;
}
