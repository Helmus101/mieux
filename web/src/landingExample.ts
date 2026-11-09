// A real result, captured from the live API on 2026-11-09 (Open Food Facts + Open Prices + retailer price lists). The best-quality alternative overall (61/100, Leader Price) has no price in any source, so the row shows the best-quality alternative that has one. Not an illustration:
// numbers, names and images are the ones the app returned for this scan. Refresh it when the data moves a lot.
export const LANDING_EXAMPLE = {
  date: '2026-11-09',
  scanned: { name: 'Excellence 70% cacao noir intense', brand: 'Lindt', size: '100 g', score: 43, perKgCents: 2435, packCents: 243, pq: 70, img: 'https://images.openfoodfacts.org/images/products/304/692/002/2651/front_en.159.200.jpg' },
  alts: [
    { key: 'cheap', name: "L'envoûtant chocolat noir 72%", brand: 'Intermarché', score: 45, perKgCents: 1480, packCents: 148, pq: 79, img: 'https://images.openfoodfacts.org/images/products/325/039/010/2625/front_fr.85.200.jpg' },
    { key: 'qualityPriced', name: 'Chocolat noir cognac de France', brand: 'Villars', score: 54, perKgCents: 3120, packCents: 312, pq: 22, img: 'https://images.openfoodfacts.org/images/products/761/003/601/1845/front_fr.11.200.jpg' },
    { key: 'value', name: 'Chocolat noir dégustation 85% cacao bio', brand: 'Bio Village · Marque Repère', score: 49, perKgCents: 1870, packCents: 187, pq: 80, img: 'https://images.openfoodfacts.org/images/products/356/470/714/2700/front_fr.94.200.jpg' },
  ],
} as const;
