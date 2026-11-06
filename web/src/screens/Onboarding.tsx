import { useState } from 'react';
import { t, setLocale } from '@shared/i18n';
import { useProfile } from '@shared/stores';
import { Button, Card, Muted, Segmented, Brand } from '../ui';
import { ACCOUNT_REQUIRED, accountEnabled, useAccount } from '../account';
import AuthForm from '../AuthForm';
import { InstallCard } from '../InstallPrompt';
import { COUNTRIES, type Country } from '@shared/chains';

export default function Onboarding({ gate = false }: { gate?: boolean }) {
  const p = useProfile();
  const [step, setStep] = useState(-1);
  const email = useAccount((a) => a.email);
  if (step === -1) return (
    <div className="ob">
      <Segmented value={p.language ?? 'fr'} onChange={(k) => { p.setLanguage(k as 'fr' | 'en'); setLocale(k as 'fr' | 'en'); }} options={[{ key: 'fr', label: 'Français' }, { key: 'en', label: 'English' }]} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <Brand size={52} big /><p className="mut" style={{ margin: '6px 0 18px' }}>{t('brand.tagline')}</p><h1 style={{ fontSize: 34 }}>{t('welcome.title')}</h1><ul className="ob-points"><li>{t('welcome.p1')}</li><li>{t('welcome.p2')}</li><li>{t('welcome.p3')}</li></ul>
      </div>
      {accountEnabled && ACCOUNT_REQUIRED && <Card>
        {email ? <b>{t('account.as', { x: email })}</b> : <>
          <p className="mut sm" style={{ margin: '0 0 10px' }}>{t('account.hint')}</p>
          <AuthForm /></>}
      </Card>}
      <InstallCard />
      <Segmented value={p.country ?? 'FR'} onChange={(k) => p.setCountry(k as Country)} options={COUNTRIES.map((c) => ({ key: c, label: t('country.' + c) }))} />
      {!gate && <Button primary disabled={accountEnabled && ACCOUNT_REQUIRED && !email} onPress={() => setStep(0)}>{t('welcome.start')}</Button>}
    </div>
  );
  // What matters most: one question, mapped to the ranking priorities. Allergies, diet, stores and address are asked later, in Profile.
  const PRESETS: [string, string[]][] = [['nutrition', ['overall']], ['money', ['budget']], ['both', ['value']]];
  const picked = PRESETS.find(([, ks]) => ks.join() === p.priorities.join())?.[0];
  return (
    <div className="ob">
      <h1 style={{ fontSize: 30 }}>{t('onboarding.mt')}</h1>
      <div style={{ marginTop: 14 }}>
        {PRESETS.map(([k, ks]) => (
          <button key={k} className={'opt' + (picked === k ? ' on' : '')} onClick={() => p.setPriorities(ks)}><b>{t('onboarding.m_' + k)}</b><span className="tick" /></button>
        ))}
      </div>
      <Muted>{t('onboarding.later')}</Muted>
      <div style={{ flex: 1 }} />
      <Button primary disabled={!picked} onPress={() => p.finish()}>{t('onboarding.start')}</Button>
      <Button plain onPress={() => setStep(-1)}>{t('common.back')}</Button>
    </div>
  );
}
