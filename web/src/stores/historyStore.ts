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
  scans: ScanEntry[]; searches: SearchEntry[]; comparisons: CompareEntry[]; receipts: ReceiptEntry[];
  addScan: (product: any) => void; addSearch: (s: Omit<SearchEntry, 'id' | 'at'>) => void; addComparison: (ids: string[], names: string[]) => void; addReceipt: (r: Omit<ReceiptEntry, 'id' | 'at'>) => void;
  productById: (id: string) => any | null; removeScan: (at: string) => void; clear: () => void; exportAll: () => unknown;
}
const K = { scans: 'fiq_h_scans', searches: 'fiq_h_searches', comparisons: 'fiq_h_comparisons', receipts: 'fiq_h_receipts' };
const now = () => new Date().toISOString();
const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);

export const useHistory = create<State>((set, get) => ({
  scans: load<ScanEntry[]>(K.scans, []), searches: load<SearchEntry[]>(K.searches, []), comparisons: load<CompareEntry[]>(K.comparisons, []),
  receipts: load<ReceiptEntry[]>(K.receipts, []),
  addScan: (product) => { const l = [{ id: product.id, at: now(), product }, ...get().scans.filter((s) => s.id !== product.id)].slice(0, 200); set({ scans: l }); save(K.scans, l); },
  addSearch: (s) => { const l = [{ ...s, id: uid(), at: now() }, ...get().searches].slice(0, 60); set({ searches: l }); save(K.searches, l); },
  addComparison: (ids, names) => { const l = [{ at: now(), ids, names }, ...get().comparisons].slice(0, 40); set({ comparisons: l }); save(K.comparisons, l); },
  addReceipt: (r) => { const l = [{ ...r, id: uid(), at: now() }, ...get().receipts]; set({ receipts: l }); save(K.receipts, l); },
  productById: (id) => get().scans.find((s) => s.id === id)?.product ?? null,
  removeScan: (at) => { const l = get().scans.filter((s) => s.at !== at); set({ scans: l }); save(K.scans, l); },
  clear: () => { set({ scans: [], searches: [], comparisons: [], receipts: [] }); [K.scans, K.searches, K.comparisons, K.receipts].forEach((k) => save(k, [])); },
  exportAll: () => { const s = get(); return { scans: s.scans, searches: s.searches, comparisons: s.comparisons, receipts: s.receipts }; },
}));

/** Re-read persisted data after the platform storage adapter has been swapped (Expo). */
export const hydrateHistory = () => useHistory.setState({
  scans: load<ScanEntry[]>(K.scans, []), searches: load<SearchEntry[]>(K.searches, []), comparisons: load<CompareEntry[]>(K.comparisons, []),
  receipts: load<ReceiptEntry[]>(K.receipts, []),
});
