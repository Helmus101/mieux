// A real result, captured from the live API on 2026-11-09 (Open Food Facts + Open Prices + retailer price lists). Not an illustration:
// numbers, names and images are the ones the app returned for this scan. Refresh it when the data moves a lot.
export const LANDING_EXAMPLE = {
  date: '2026-11-09',
  scanned: { name: 'Excellence 70% cacao noir intense', brand: 'Lindt', size: '100 g', score: 43, perKgCents: 2435, packCents: 243, pq: 70, img: 'https://images.openfoodfacts.org/images/products/304/692/002/2651/front_en.159.200.jpg' },
  alts: [
    { key: 'cheap', name: "L'envoûtant chocolat noir 72%", brand: 'Intermarché', score: 45, perKgCents: 1480, packCents: 148, pq: 79, img: 'https://images.openfoodfacts.org/images/products/325/039/010/2625/front_fr.85.200.jpg' },
    { key: 'quality', name: 'Chocolat noir (ligne)', brand: 'Leader Price', score: 61, perKgCents: null, packCents: null, pq: null, img: 'https://images.openfoodfacts.org/images/products/326/385/221/3012/front_fr.24.200.jpg' },
    { key: 'value', name: 'Chocolat noir dégustation 85% cacao bio', brand: 'Bio Village · Marque Repère', score: 49, perKgCents: 1870, packCents: 187, pq: 80, img: 'https://images.openfoodfacts.org/images/products/356/470/714/2700/front_fr.94.200.jpg' },
  ],
} as const;
