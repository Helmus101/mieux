import { api } from '@shared/api/client';
// Home location. Stored only on this device (profile store); used to rank recommendations by nearby shops and to start directions.
export interface Home { city: string; postcode: string | null; lat?: number; lon?: number; label?: string; exact?: boolean }

/** Typed address -> up to 5 formatted suggestions, through our API (which asks France's public address service). */
export async function searchAddress(q: string): Promise<Home[]> {
  if (q.trim().length < 3) return [];
  try { return await api.searchAddress(q); } catch { return []; }
}

/** Google Maps directions from home (or the current position when home is unknown) to a shop. */
export const directionsUrl = (to: { lat: number; lon: number }, from?: { lat?: number; lon?: number } | null) =>
  `https://www.google.com/maps/dir/?api=1&destination=${to.lat},${to.lon}${from?.lat != null ? `&origin=${from.lat},${from.lon}` : ''}&travelmode=walking`;
