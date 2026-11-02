import { create } from 'zustand';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { api } from '@shared/api/client';

const URL = (import.meta.env.VITE_SUPABASE_URL as string | undefined) || 'https://nhlazqawxthoaymwrrze.supabase.co';
const KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

/** Supabase is used for sign-in only; null until the anon key is configured, in which case the app stays account-free. */
export const supabase: SupabaseClient | null = KEY ? createClient(URL, KEY, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } }) : null;
export const accountEnabled = !!supabase;

interface Account { email: string | null; uid: string | null; ready: boolean; scans: number | null }
export const useAccount = create<Account>(() => ({ email: null, uid: null, ready: !supabase, scans: null }));

/* The scan total is counted on the device and never read back from Supabase (saves egress).
 * It is written once, when a new week starts: a single request that adds last week's scans to the account total. */
interface Local { total: number; pending: number; week: string }
const storeKey = (uid: string) => `fiq_scans_${uid}`;
const readLocal = (uid: string): Local => { try { return { total: 0, pending: 0, week: '', ...JSON.parse(localStorage.getItem(storeKey(uid)) ?? '{}') }; } catch { return { total: 0, pending: 0, week: '' }; } };
const writeLocal = (uid: string, v: Local) => { try { localStorage.setItem(storeKey(uid), JSON.stringify(v)); } catch { /* storage unavailable: the count simply is not kept */ } };
/** Monday of the current week, as YYYY-MM-DD. */
export const weekStart = (d = new Date()) => { const m = new Date(d.getFullYear(), d.getMonth(), d.getDate() - ((d.getDay() + 6) % 7)); return `${m.getFullYear()}-${String(m.getMonth() + 1).padStart(2, '0')}-${String(m.getDate()).padStart(2, '0')}`; };

/** Counts one scan locally. No network. */
export const countScan = () => {
  const uid = useAccount.getState().uid;
  if (!uid) return;
  const l = readLocal(uid);
  l.total += 1; l.pending += 1; l.week = l.week || weekStart();
  writeLocal(uid, l);
  useAccount.setState({ scans: l.total });
};

/** Write-only: when a new week has begun, send the scans counted since the last write (one request, no data returned). */
export const syncScans = async () => {
  const { uid } = useAccount.getState();
  if (!supabase || !uid) return;
  const l = readLocal(uid), now = weekStart();
  useAccount.setState({ scans: l.total });
  if (!l.week) { writeLocal(uid, { ...l, week: now }); return; }  // first run: the first write happens when this week ends
  if (l.week >= now || l.pending <= 0) return;
  const sent = l.pending;
  const { error } = await supabase.rpc('add_scans', { n: sent });
  if (!error) { const cur = readLocal(uid); writeLocal(uid, { ...cur, pending: Math.max(0, cur.pending - sent), week: now }); }
};

let started = false;
/** Call once at startup: restores the session, keeps the API token fresh, and clears it on sign-out. */
export function initAccount() {
  if (!supabase || started) return;
  started = true;
  const apply = (session: { access_token: string; user: { id: string; email?: string | null } } | null) => {
    if (session) { api.setToken(session.access_token); useAccount.setState({ email: session.user.email ?? null, uid: session.user.id, ready: true }); syncScans(); }
    else { api.clearToken(); useAccount.setState({ email: null, uid: null, ready: true, scans: null }); }
  };
  supabase.auth.getSession().then(({ data }) => apply(data.session));
  supabase.auth.onAuthStateChange((_event, session) => apply(session));
}

export type AuthResult = 'ok' | 'confirm' | 'invalid' | 'exists' | 'weak' | 'error';

const classify = (message: string): AuthResult => {
  const m = message.toLowerCase();
  if (m.includes('already') || m.includes('registered')) return 'exists';
  if (m.includes('password') && (m.includes('least') || m.includes('weak') || m.includes('short'))) return 'weak';
  if (m.includes('invalid') || m.includes('credentials')) return 'invalid';
  return 'error';
};

/** One form for everyone: try to sign in; if there is no such account yet, create it.
 *  With "Confirm email" switched off in Supabase, sign-up returns a session straight away. */
export async function continueWithPassword(email: string, password: string): Promise<AuthResult> {
  const { error } = await supabase!.auth.signInWithPassword({ email, password });
  if (!error) return 'ok';
  if (classify(error.message) !== 'invalid') return classify(error.message);
  const { data, error: upErr } = await supabase!.auth.signUp({ email, password });
  if (upErr) { const r = classify(upErr.message); return r === 'exists' ? 'invalid' : r; }  // the account exists, so the password was wrong
  return data.session ? 'ok' : 'confirm';
}

export const signOut = () => supabase!.auth.signOut();
