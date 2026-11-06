import { create } from 'zustand';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { api } from '@shared/api/client';
import { hydrateProfile, useProfile } from '@shared/stores/profileStore';
import { hydrateHistory } from '@shared/stores/historyStore';
import { setAccountId } from '@shared/storage';

const URL = (import.meta.env.VITE_SUPABASE_URL as string | undefined) || 'https://nhlazqawxthoaymwrrze.supabase.co';
const KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

/** Supabase is used for sign-in only; null until the anon key is configured, in which case the app stays account-free. */
/** Sign-in is switched off for now: the app is account-free (anonymous session, history and profile stay on the device). Set to true to bring sign-in back; nothing else changes. */
const AUTH_ENABLED = false;
export const supabase: SupabaseClient | null = AUTH_ENABLED && KEY ? createClient(URL, KEY, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } }) : null;
export const accountEnabled = !!supabase;

interface Account { email: string | null; uid: string | null; ready: boolean; scans: number | null; pending: number; syncError: string | null }
export const useAccount = create<Account>(() => ({ email: null, uid: null, ready: !supabase, scans: null, pending: 0, syncError: null }));

/* Every scan is added to the account total in Supabase right away (a write-only call that returns nothing: no egress).
 * The total shown in Profile is counted on the device and never read back. If a write fails (offline), the scans wait and go out with the next one. */
interface Local { total: number; pending: number }
const storeKey = (uid: string) => `fiq_scans_${uid}`;
const readLocal = (uid: string): Local => { try { return { total: 0, pending: 0, ...JSON.parse(localStorage.getItem(storeKey(uid)) ?? '{}') }; } catch { return { total: 0, pending: 0 }; } };
const writeLocal = (uid: string, v: Local) => { try { localStorage.setItem(storeKey(uid), JSON.stringify(v)); } catch { /* storage unavailable: the count simply is not kept */ } };

let flushing: Promise<void> | null = null;
/** Sends the scans that are waiting. One write at a time, so a scan during a send is picked up right after instead of being counted twice. */
export const syncScans = (): Promise<void> => (flushing ??= doFlush().finally(() => { flushing = null; }));

const doFlush = async () => {
  for (let i = 0; i < 5; i++) {
    const { uid } = useAccount.getState();
    if (!supabase || !uid) return;
    const l = readLocal(uid);
    useAccount.setState({ scans: l.total, pending: l.pending });
    if (l.pending <= 0) return;
    const { error } = await supabase.rpc('add_scans', { n: l.pending });
    if (error) { console.warn('add_scans failed', error); useAccount.setState({ syncError: error.message || error.code || 'error' }); return; }
    const cur = readLocal(uid);
    const left = Math.max(0, cur.pending - l.pending);
    writeLocal(uid, { ...cur, pending: left });
    useAccount.setState({ pending: left, syncError: null });
  }
};

let lastCounted = { code: '', at: 0 };
/** Counts one scan and sends it. The same product within 30 s is one scan (a screen can render its effect twice). */
export const countScan = (code: string) => {
  const uid = useAccount.getState().uid;
  if (!uid) return;
  if (code === lastCounted.code && Date.now() - lastCounted.at < 30000) return;
  lastCounted = { code, at: Date.now() };
  const l = readLocal(uid);
  l.total += 1; l.pending += 1;
  writeLocal(uid, l);
  useAccount.setState({ scans: l.total, pending: l.pending });
  syncScans();
};


let started = false;
/** Call once at startup: restores the session, keeps the API token fresh, and clears it on sign-out. */
export function initAccount() {
  if (!supabase || started) return;
  started = true;
  let current: string | null | undefined;  // undefined = nothing applied yet
  const apply = (session: { access_token: string; user: { id: string; email?: string | null } } | null) => {
    const uid = session?.user.id ?? null;
    if (session) api.setToken(session.access_token); else api.clearToken();
    if (uid === current) return;  // token refresh or repeated event for the same account: nothing to switch, and the screen must not flicker
    // Switching account: point local storage at that account's keys, then reload the stores from them. Language chosen before signing in carries over.
    const lang = useProfile.getState().language;
    current = uid;
    setAccountId(uid);
    hydrateProfile();
    hydrateHistory();
    if (uid && !useProfile.getState().onboarded && lang) useProfile.getState().setLanguage(lang);
    useAccount.setState({ email: session?.user.email ?? null, uid, ready: true, scans: null, pending: 0, syncError: null });
    if (uid) { syncScans(); checkStillExists(uid); }
  };
  // The account may have been deleted elsewhere while this device still holds its session: confirm in the background and sign out if so. A network failure never signs anyone out.
  const checkStillExists = async (uid: string) => {
    const { error } = await supabase.auth.getUser();
    if (error && current === uid && /not.?found|does not exist|user_not_found|jwt|invalid.*(token|claim)/i.test(`${error.code ?? ''} ${error.message}`) && (error.status === undefined || [401, 403, 404].includes(error.status))) {
      await supabase.auth.signOut({ scope: 'local' }).catch(() => undefined);
      apply(null);
    }
  };
  // Open instantly for a returning user: the saved session is on the device, so trust it now and let Supabase confirm (or refresh an expired token over the network) in the background.
  try {
    const saved = JSON.parse(localStorage.getItem(`sb-${new globalThis.URL(URL).hostname.split('.')[0]}-auth-token`) ?? 'null');
    if (saved?.access_token && saved?.user?.id) apply(saved);
  } catch { /* nothing saved: the normal path below decides */ }
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
