import { t } from './i18n';

/* eslint-disable @typescript-eslint/no-explicit-any */
export type Tone = 'w' | 'b' | undefined;
const label = (x: any) => (x.priority.startsWith('allergen:') ? t('diets.' + x.priority.split(':')[1]) : t('priorities.' + x.priority));

/** One plain-language sentence about how a scanned product fits the user's restrictions and priorities. Platform-free: used by web and Expo. */
export function verdictOf(fit: any[]): { tone: Tone; text: string } | null {
  const bad = fit.filter((x) => x.status === 'conflict');
  const check = fit.filter((x) => x.status === 'unknown' || x.status === 'no_match');
  if (bad.length) return { tone: 'b', text: t('simple.verdictConflict', { x: bad.map(label).join(', ') }) };
  if (check.length) return { tone: 'w', text: t('simple.verdictCheck', { x: check.map(label).join(', ') }) };
  return fit.length ? { tone: undefined, text: t('simple.verdictOk') } : null;
}

/** The single price figure shown first. 'real' = observed (receipt/community), 'estimate' = opt-in estimate, 'none' = unknown. cents per kg. */
export function priceHeadline(pc: any): { kind: 'real' | 'estimate' | 'none'; perKgCents?: number } {
  const kg = pc?.indicators?.price_per_kg_eur;
  if (kg != null && kg > 0) return { kind: 'real', perKgCents: Math.round(kg * 100) };
  const est = pc?.estimate?.per100_cents;
  if (est != null && est > 0) return { kind: 'estimate', perKgCents: Math.round(est * 10) };
  return { kind: 'none' };
}
