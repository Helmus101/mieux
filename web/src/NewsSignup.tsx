import { useState } from 'react';
import { api } from '@shared/api/client';
import { Button, Card, Muted } from './ui';

const KEY = 'mx_news';   // 'done' (subscribed) | 'no' (dismissed): the prompt is shown at most once
export const newsState = () => { try { return localStorage.getItem(KEY); } catch { return null; } };
const setNews = (v: string) => { try { localStorage.setItem(KEY, v); } catch { /* storage unavailable */ } };

/** Optional news by email. Nothing is sent until the consent box (unticked) is ticked and the person presses the button. */
export default function NewsSignup({ onDone, dismissible }: { onDone?: () => void; dismissible?: boolean }) {
  const [email, setEmail] = useState(''), [ok, setOk] = useState(false), [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false), [msg, setMsg] = useState<string | null>(null);

  const send = async () => {
    setBusy(true); setMsg(null);
    try { await api.subscribeNews(email.trim(), consent); setNews('done'); setOk(true); onDone?.(); }
    catch (e: unknown) { setMsg((e as { response?: { status?: number } })?.response?.status === 422 ? 'Vérifiez l\'adresse e-mail.' : 'Impossible d\'enregistrer pour l\'instant, réessayez.'); }
    finally { setBusy(false); }
  };
  // Really writes a throwaway address on the server and reports where it was saved.
  const test = async () => {
    setBusy(true); setMsg(null);
    try {
      const r = await api.testNews();
      setMsg(`Serveur : OK · Supabase : ${r.supabase === 'ok' ? 'OK' : r.supabase === 'off' ? 'non configuré' : 'ÉCHEC'}`);
    } catch { setMsg('Test échoué : le serveur ne répond pas.'); }
    finally { setBusy(false); }
  };

  if (ok) return <Card><b>Merci !</b><Muted>Vous recevrez les nouveautés de Mieux. Désinscription : écrivez-nous.</Muted></Card>;
  return (
    <Card>
      <b>Recevoir les nouveautés de Mieux</b>
      <Muted>Quelques e-mails au plus, pour les nouvelles fonctions. Rien d'autre n'est demandé.</Muted>
      <input type="email" inputMode="email" autoComplete="email" placeholder="vous@exemple.fr" value={email} onChange={(e) => setEmail(e.target.value)}
        style={{ width: '100%', boxSizing: 'border-box', margin: '12px 0 8px', padding: '12px 14px', borderRadius: 10, border: '1px solid var(--line)', font: 'inherit', fontSize: 16 }} />
      <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 13, margin: '4px 0 12px' }}>
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} style={{ marginTop: 3 }} />
        <span>J'accepte que Mieux enregistre mon adresse pour m'envoyer ses nouveautés. Je peux me désinscrire à tout moment (<a href="/confidentialite">confidentialité</a>).</span>
      </label>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <Button onPress={send} disabled={busy || !consent || !email.includes('@')}>S'inscrire</Button>
        {dismissible && <Button plain onPress={() => { setNews('no'); onDone?.(); }}>Non merci</Button>}
        <button type="button" onClick={test} disabled={busy} style={{ marginLeft: 'auto', background: 'none', border: 0, color: 'var(--mut)', fontSize: 12, textDecoration: 'underline' }}>Tester</button>
      </div>
      {msg && <p style={{ margin: '10px 0 0', fontSize: 13 }}>{msg}</p>}
    </Card>
  );
}

/** Shown once, after 50 scanned products, never on the scanner. Dismissable; "Non merci" or signing up ends it for good. */
export function NewsPrompt({ scans, onScanner }: { scans: number; onScanner: boolean }) {
  const [gone, setGone] = useState(false);
  if (gone || onScanner || scans < 50 || newsState()) return null;
  return <div style={{ position: 'fixed', left: 12, right: 12, bottom: 'calc(84px + env(safe-area-inset-bottom))', zIndex: 40, maxWidth: 480, margin: '0 auto' }}><NewsSignup dismissible onDone={() => setGone(true)} /></div>;
}
