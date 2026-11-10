// One place that builds the alternatives request from the profile, so the product page can start it early and the alternatives
// screen gets the very same answer (same key) instead of asking again. In-flight requests are shared: opening the screen while the
// early request is still running waits for it rather than starting a second, slower one.
import { api } from '@shared/api/client';
import { useProfile } from '@shared/stores';
import { chainsFor } from '@shared/chains';
import { readCache, writeCache } from './swr';

/* eslint-disable @typescript-eslint/no-explicit-any */
export const NEAR_KM = 5; // only products sold at a chain with a branch within 5 km of home: fixed, not a setting

export function altRequest(barcode: string) {
  const p = useProfile.getState();
  const q = p.priorities.filter((k: string) => k !== 'budget' && k !== 'value');
  const prios = q.length ? q : ['overall'];
  const chains = (p.chains ?? []).filter((id: string) => chainsFor(p.country).some((c) => c.id === id));
  const home = p.place, hasHome = home?.lat != null;
  const key = `alt:${barcode}:${prios.join()}:${chains.join()}`;
  const body = { priorities: prios, category_mode: 'similar', limit: 20, substitution_max: 2, same_size: false, chains, price_constraint: 'any', approximate: p.estimates, ...(hasHome ? { location: { lat: home!.lat, lon: home!.lon, radius_km: NEAR_KM } } : {}) };
  return { key, body, prios, chains };
}

const inflight = new Map<string, Promise<any>>();

/** Fresh answer for this barcode and the current profile; a request already under way for the same key is reused. */
export function fetchAlternatives(barcode: string): Promise<any> {
  const { key, body } = altRequest(barcode);
  const running = inflight.get(key);
  if (running) return running;
  const p = api.getAlternatives(barcode, body).then((x: any) => { writeCache(key, x); return x; }).finally(() => inflight.delete(key));
  inflight.set(key, p);
  return p;
}

/** The last answer shown at once (if any), then the fresh one. */
export const cachedAlternatives = (barcode: string) => readCache<any>(altRequest(barcode).key);

/** Called by the product page: starts the search in the background so the alternatives screen opens complete. */
export function prefetchAlternatives(barcode: string) {
  if (cachedAlternatives(barcode)) return;
  fetchAlternatives(barcode).catch(() => undefined);
}
