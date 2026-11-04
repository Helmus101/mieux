import { useState } from 'react';
import { t } from '@shared/i18n';
import { Button } from './ui';
import { continueWithPassword, type AuthResult } from './account';

/** One email + password form: signs in, or creates the account when there is none. */
export default function AuthForm() {
  const [email, setEmail] = useState(''), [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false), [res, setRes] = useState<AuthResult | null>(null);
  const valid = /^\S+@\S+\.\S+$/.test(email.trim()) && password.length >= 6;
  const submit = async () => { setBusy(true); setRes(null); setRes(await continueWithPassword(email.trim(), password)); setBusy(false); };
  return (
    <form onSubmit={(e) => { e.preventDefault(); if (valid && !busy) void submit(); }}>
      <input type="email" value={email} onChange={(e) => { setEmail(e.target.value); setRes(null); }} placeholder={t('account.email')} autoComplete="email username" inputMode="email" aria-label={t('account.email')} />
      <input type="password" value={password} onChange={(e) => { setPassword(e.target.value); setRes(null); }} placeholder={t('account.password')} autoComplete="current-password" style={{ marginTop: 10 }} aria-label={t('account.password')} />
      <Button primary disabled={!valid || busy}>{busy ? t('common.loading') : t('account.continue')}</Button>
      {res && res !== 'ok' && <p role="alert" style={{ color: 'var(--warn)', margin: '10px 0 0' }}>{t('account.err_' + res)}</p>}
    </form>
  );
}
