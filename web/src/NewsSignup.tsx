import { useState } from 'react';
import { api } from '@shared/api/client';

const KEY = 'mx_news';   // 'done' once an address has been saved
export const newsState = () => { try { return localStorage.getItem(KEY); } catch { return null; } };
const setDone = () => { try { localStorage.setItem(KEY, 'done'); } catch { /* storage unavailable */ } };

/** The e-mail popup. `required`: no way to close it until an address is saved (shown after 20 scanned products).
 *  Otherwise (opened from Profile) it can be closed with the × or by tapping outside. */
export function NewsModal({ required, onClose }: { required?: boolean; onClose: () => void }) {
  const [email, setEmail] = useState(''), [busy, setBusy] = useState(false), [msg, setMsg] = useState<string | null>(null), [ok, setOk] = useState(false);
  const valid = /^[^@\s]+@[^@\s]+\.[^@\s.]{2,}$/.test(email.trim());

  const send = async () => {
    setBusy(true); setMsg(null);
    try { await api.subscribeNews(email.trim(), true); setDone(); setOk(true); setTimeout(onClose, 1400); }
    catch (e: unknown) { setMsg((e as { response?: { status?: number } })?.response?.status === 422 ? 'Vérifiez l\'adresse e-mail.' : 'Impossible d\'enregistrer pour l\'instant, réessayez.'); }
    finally { setBusy(false); }
  };

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="news-title" onClick={() => { if (!required) onClose(); }}
      style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(20,32,26,.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ position: 'relative', width: '100%', maxWidth: 420, background: 'var(--card, #fff)', borderRadius: 18, padding: '24px 20px 20px', boxShadow: '0 20px 60px rgba(0,0,0,.25)' }}>
        {!required && <button type="button" aria-label="Fermer" onClick={onClose} style={{ position: 'absolute', top: 6, right: 6, width: 44, height: 44, border: 0, background: 'none', fontSize: 26, lineHeight: 1, color: 'var(--mut)', cursor: 'pointer' }}>×</button>}
        {ok ? (
          <><b id="news-title" style={{ fontSize: 20 }}>Merci !</b><p style={{ margin: '8px 0 0', color: 'var(--mut)' }}>Votre adresse est enregistrée.</p></>
        ) : (
          <>
            <b id="news-title" style={{ fontSize: 20 }}>{required ? 'Une dernière étape pour continuer' : 'Recevoir les nouveautés de Mieux'}</b>
            <p style={{ margin: '8px 0 14px', color: 'var(--mut)', fontSize: 14.5, lineHeight: 1.5 }}>
              {required ? 'Laissez votre e-mail pour continuer à utiliser Mieux. ' : ''}Nous l'utilisons uniquement pour vous écrire quand Mieux évolue, jamais pour autre chose, et nous ne le partageons avec personne. Désinscription à tout moment (<a href="/confidentialite">confidentialité</a>).
            </p>
            <input type="email" inputMode="email" autoComplete="email" autoFocus placeholder="vous@exemple.fr" value={email} onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && valid && !busy) send(); }}
              style={{ width: '100%', boxSizing: 'border-box', padding: '13px 14px', borderRadius: 10, border: '1px solid var(--line)', font: 'inherit', fontSize: 16 }} />
            <button type="button" className="btn primary" disabled={busy || !valid} onClick={send} style={{ width: '100%', marginTop: 12 }}>{required ? 'Continuer' : 'S\'inscrire'}</button>
            {msg && <p style={{ margin: '10px 0 0', fontSize: 13, color: 'var(--bad)' }}>{msg}</p>}
          </>
        )}
      </div>
    </div>
  );
}

/** After 20 scanned products, until an address is saved. Shown on every screen. */
export function NewsPrompt({ scans }: { scans: number }) {
  const [done, setDone2] = useState(false);
  if (done || scans < 20 || newsState()) return null;
  return <NewsModal required onClose={() => setDone2(true)} />;
}
