import { create } from 'zustand';
import { load, save } from '@shared/storage';

/* eslint-disable @typescript-eslint/no-explicit-any */
// Everything the user does is also kept on the device (not only in the local server database), so the app works
// offline and a future Expo build can run without a server. Product snapshots allow offline viewing.
export interface ScanEntry { id: string; at: string; product: any }
export interface SearchEntry { id: string; at: string; originalId: string; originalName: string; priorities: string[]; mode: string; results: { id: string; name: string; brand: string | null; priceCents: number | null }[] }
export interface CompareEntry { at: string; ids: string[]; names: string[] }
export interface ReceiptEntry { id: string; at: string; retailer: string | null; date: string | null; totalCents: number; items: { raw: string; lineTotalCents: number; matched: string | null }[] }

interface State {
  scans: ScanEntry[]; searches: SearchEntry[]; comparisons: CompareEntry[]; receipts: ReceiptEntry[]; favourites: string[]; favSnapshots: Record<string, any>;
  addScan: (product: any) => void; addSearch: (s: Omit<SearchEntry, 'id' | 'at'>) => void; addComparison: (ids: string[], names: string[]) => void; addReceipt: (r: Omit<ReceiptEntry, 'id' | 'at'>) => void;
  toggleFavourite: (product: any) => void; productById: (id: string) => any | null; removeScan: (at: string) => void; clear: () => void; exportAll: () => unknown;
}
const K = { scans: 'fiq_h_scans', searches: 'fiq_h_searches', comparisons: 'fiq_h_comparisons', receipts: 'fiq_h_receipts', fav: 'fiq_favs', favSnap: 'fiq_fav_snap' };
const now = () => new Date().toISOString();
const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);

export const useHistory = create<State>((set, get) => ({
  scans: load<ScanEntry[]>(K.scans, []), searches: load<SearchEntry[]>(K.searches, []), comparisons: load<CompareEntry[]>(K.comparisons, []),
  receipts: load<ReceiptEntry[]>(K.receipts, []), favourites: load<string[]>(K.fav, []), favSnapshots: load<Record<string, any>>(K.favSnap, {}),
  addScan: (product) => { const l = [{ id: product.id, at: now(), product }, ...get().scans.filter((s) => s.id !== product.id)].slice(0, 200); set({ scans: l }); save(K.scans, l); },
  addSearch: (s) => { const l = [{ ...s, id: uid(), at: now() }, ...get().searches].slice(0, 60); set({ searches: l }); save(K.searches, l); },
  addComparison: (ids, names) => { const l = [{ at: now(), ids, names }, ...get().comparisons].slice(0, 40); set({ comparisons: l }); save(K.comparisons, l); },
  addReceipt: (r) => { const l = [{ ...r, id: uid(), at: now() }, ...get().receipts]; set({ receipts: l }); save(K.receipts, l); },
  toggleFavourite: (product) => {
    const has = get().favourites.includes(product.id);
    const fav = has ? get().favourites.filter((x) => x !== product.id) : [...get().favourites, product.id];
    const snap = { ...get().favSnapshots }; if (has) delete snap[product.id]; else snap[product.id] = product;
    set({ favourites: fav, favSnapshots: snap }); save(K.fav, fav); save(K.favSnap, snap);
  },
  productById: (id) => get().scans.find((s) => s.id === id)?.product ?? get().favSnapshots[id] ?? null,
  removeScan: (at) => { const l = get().scans.filter((s) => s.at !== at); set({ scans: l }); save(K.scans, l); },
  clear: () => { set({ scans: [], searches: [], comparisons: [], receipts: [], favourites: [], favSnapshots: {} }); [K.scans, K.searches, K.comparisons, K.receipts, K.fav, K.favSnap].forEach((k) => save(k, k === K.favSnap ? {} : [])); },
  exportAll: () => { const s = get(); return { scans: s.scans, searches: s.searches, comparisons: s.comparisons, receipts: s.receipts, favourites: s.favourites }; },
}));

/** Re-read persisted data after the platform storage adapter has been swapped (Expo). */
export const hydrateHistory = () => useHistory.setState({
  scans: load<ScanEntry[]>(K.scans, []), searches: load<SearchEntry[]>(K.searches, []), comparisons: load<CompareEntry[]>(K.comparisons, []),
  receipts: load<ReceiptEntry[]>(K.receipts, []), favourites: load<string[]>(K.fav, []), favSnapshots: load<Record<string, any>>(K.favSnap, {}),
});
