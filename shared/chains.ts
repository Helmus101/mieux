// Supermarket chains Mieux knows (ids match the backend retail_chains table).
export const FR_CHAINS: { id: string; name: string }[] = [
  { id: 'carrefour', name: 'Carrefour' }, { id: 'leclerc', name: 'E.Leclerc' }, { id: 'intermarche', name: 'Intermarché' }, { id: 'auchan', name: 'Auchan' }, { id: 'lidl', name: 'Lidl' },
  { id: 'monoprix', name: 'Monoprix' }, { id: 'superu', name: 'Super U' }, { id: 'aldi', name: 'Aldi' }, { id: 'franprix', name: 'Franprix' }, { id: 'casino', name: 'Casino' },
  { id: 'picard', name: 'Picard' }, { id: 'biocoop', name: 'Biocoop' }, { id: 'naturalia', name: 'Naturalia' }, { id: 'lavieclaire', name: 'La Vie Claire' }, { id: 'grandfrais', name: 'Grand Frais' }, { id: 'cora', name: 'Cora' }, { id: 'match', name: 'Match' },
];

// US chains. Aldi and Lidl trade in both countries and keep the same ids. Ids match the backend retail_chains table.
export const US_CHAINS: { id: string; name: string }[] = [
  { id: 'walmart', name: 'Walmart' }, { id: 'kroger', name: 'Kroger' }, { id: 'costco', name: 'Costco' }, { id: 'target', name: 'Target' }, { id: 'albertsons', name: 'Albertsons' },
  { id: 'safeway', name: 'Safeway' }, { id: 'publix', name: 'Publix' }, { id: 'wholefoods', name: 'Whole Foods' }, { id: 'traderjoes', name: "Trader Joe's" }, { id: 'aldi', name: 'Aldi' },
  { id: 'lidl', name: 'Lidl' }, { id: 'heb', name: 'H-E-B' }, { id: 'wegmans', name: 'Wegmans' }, { id: 'sprouts', name: 'Sprouts' }, { id: 'foodlion', name: 'Food Lion' },
  { id: 'stopshop', name: 'Stop & Shop' }, { id: 'meijer', name: 'Meijer' }, { id: 'sams', name: "Sam's Club" }, { id: 'bjs', name: "BJ's" }, { id: 'hyvee', name: 'Hy-Vee' },
  { id: 'shoprite', name: 'ShopRite' }, { id: 'harristeeter', name: 'Harris Teeter' }, { id: 'winndixie', name: 'Winn-Dixie' },
];

export type Country = 'FR' | 'US';
export const COUNTRIES: Country[] = ['FR', 'US'];
export const chainsFor = (country?: Country | null) => (country === 'US' ? US_CHAINS : FR_CHAINS);
/** Kept for existing imports: the French list. Prefer chainsFor(country). */
export const CHAIN_LIST = FR_CHAINS;
