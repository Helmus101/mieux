import { create } from 'zustand';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { api } from '@shared/api/client';

const URL = (import.meta.env.VITE_SUPABASE_URL as string | undefined) || 'https://nhlazqawxthoaymwrrze.supabase.co';
const KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

/** Supabase is used for sign-in only; null until the anon key is configured, in which case the app stays account-free. */
export const supabase: SupabaseClient | null = KEY ? createClient(URL, KEY, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } }) : null;
export const accountEnabled = !!supabase;

interface Account { email: string | null; ready: boolean; scans: number | null }
export const useAccount = create<Account>(() => ({ email: null, ready: !supabase, scans: null }));

/** The total number of scans is the only thing an account keeps; everything else stays on the device. */
export const refreshScanCount = async () => {
  if (!supabase) return;
  const { data } = await supabase.from('scan_counts').select('scans').maybeSingle();
  useAccount.setState({ scans: data?.scans ?? 0 });
};

/** Adds one to this account's total in Supabase (the function is the only way to change it). */
export const countScan = async () => {
  if (!supabase || !useAccount.getState().email) return;
  const { data } = await supabase.rpc('increment_scans');
  if (typeof data === 'number') useAccount.setState({ scans: data });
};

let started = false;
/** Call once at startup: restores the session, keeps the API token fresh, and clears it on sign-out. */
export function initAccount() {
  if (!supabase || started) return;
  started = true;
  const apply = (session: { access_token: string; user: { email?: string | null } } | null) => {
    if (session) { api.setToken(session.access_token); useAccount.setState({ email: session.user.email ?? null, ready: true }); refreshScanCount(); }
    else { api.clearToken(); useAccount.setState({ email: null, ready: true, scans: null }); }
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
