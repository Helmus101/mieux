// Home location. Stored only on this device (profile store); used to rank recommendations by nearby shops and to start directions.
// Browser geolocation gives the position; France's public address service (api-adresse.data.gouv.fr) turns coordinates or typed text into an address.
export interface Home { city: string; postcode: string | null; lat?: number; lon?: number; label?: string; exact?: boolean }

const here = () => new Promise<GeolocationPosition | null>((ok) => navigator.geolocation ? navigator.geolocation.getCurrentPosition(ok, () => ok(null), { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 }) : ok(null));

const fromFeature = (f: any): Home => ({ city: f.properties.city, postcode: f.properties.postcode ?? null, lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0], label: f.properties.label, exact: f.properties.type === 'housenumber' });

/** Current position -> nearest address. Falls back to the raw coordinates if the address service is unreachable. */
export async function findCity(): Promise<Home | 'denied' | null> {
  const pos = await here();
  if (!pos) return 'denied';
  const { latitude: lat, longitude: lon } = pos.coords;
  try {
    const j = await (await fetch(`https://api-adresse.data.gouv.fr/reverse/?lat=${lat}&lon=${lon}&type=housenumber`)).json();
    const f = j?.features?.[0];
    return f ? fromFeature(f) : { city: '', postcode: null, lat, lon };
  } catch { return { city: '', postcode: null, lat, lon }; }
}

/** Typed address -> up to 5 suggestions. */
export async function searchAddress(q: string): Promise<Home[]> {
  if (q.trim().length < 4) return [];
  try {
    const j = await (await fetch(`https://api-adresse.data.gouv.fr/search/?q=${encodeURIComponent(q)}&limit=8&autocomplete=1`)).json();
    return (j.features ?? []).map(fromFeature).sort((a: Home, b: Home) => Number(!!b.exact) - Number(!!a.exact)).slice(0, 5);
  } catch { return []; }
}

/** Google Maps directions from home (or the current position when home is unknown) to a shop. */
export const directionsUrl = (to: { lat: number; lon: number }, from?: { lat?: number; lon?: number } | null) =>
  `https://www.google.com/maps/dir/?api=1&destination=${to.lat},${to.lon}${from?.lat != null ? `&origin=${from.lat},${from.lon}` : ''}&travelmode=walking`;
