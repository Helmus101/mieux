// Scan counter kept on the device only: no account, no sync. Every scan adds one to a local total.
const KEY = 'fiq_scans_total';
const read = (): number => { try { return Math.max(0, Number(localStorage.getItem(KEY)) || 0); } catch { return 0; } };
const write = (n: number) => { try { localStorage.setItem(KEY, String(Math.max(0, n))); } catch { /* storage unavailable */ } };

let lastCounted = { code: '', at: 0 };
/** Counts one scan. The same product within 30 s is one scan (a screen can render its effect twice). */
export const countScan = (_code: string) => {
  if (lastCounted.code === _code && Date.now() - lastCounted.at < 30000) return;
  lastCounted = { code: _code, at: Date.now() };
  write(read() + 1);
};
