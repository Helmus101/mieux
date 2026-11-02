import { create } from 'zustand';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { api } from '@shared/api/client';

const URL = (import.meta.env.VITE_SUPABASE_URL as string | undefined) || 'https://nhlazqawxthoaymwrrze.supabase.co';
const KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

/** Supabase is used for sign-in only; null until the anon key is configured, in which case the app stays account-free. */
export const supabase: SupabaseClient | null = KEY ? createClient(URL, KEY, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } }) : null;
export const accountEnabled = !!supabase;

interface Account { email: string | null; ready: boolean }
export const useAccount = create<Account>(() => ({ email: null, ready: !supabase }));

let started = false;
/** Call once at startup: restores the session, keeps the API token fresh, and clears it on sign-out. */
export function initAccount() {
  if (!supabase || started) return;
  started = true;
  const apply = (session: { access_token: string; user: { email?: string | null } } | null) => {
    if (session) { api.setToken(session.access_token); useAccount.setState({ email: session.user.email ?? null, ready: true }); }
    else { api.clearToken(); useAccount.setState({ email: null, ready: true }); }
  };
  supabase.auth.getSession().then(({ data }) => apply(data.session));
  supabase.auth.onAuthStateChange((_event, session) => apply(session));
}

export const sendMagicLink = (email: string) => supabase!.auth.signInWithOtp({ email, options: { emailRedirectTo: `${window.location.origin}/app` } });
export const signOut = () => supabase!.auth.signOut();
