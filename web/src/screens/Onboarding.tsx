import { t, setLocale } from '@shared/i18n';
import { useProfile } from '@shared/stores';
import { routes, useNav } from '../nav';
import { Button, Card, Segmented, Brand } from '../ui';
import { ACCOUNT_REQUIRED, accountEnabled, useAccount } from '../account';
import AuthForm from '../AuthForm';
import { COUNTRIES, type Country } from '@shared/chains';

export default function Onboarding({ gate = false }: { gate?: boolean }) {
  const p = useProfile();
  const { go } = useNav();   // when onboarding ends the person lands on the scanner, wherever the URL pointed
  const email = useAccount((a) => a.email);
  return (
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
      {COUNTRIES.length > 1 && <Segmented value={p.country ?? 'FR'} onChange={(k) => p.setCountry(k as Country)} options={COUNTRIES.map((c) => ({ key: c, label: t('country.' + c) }))} />}
      {!gate && <Button primary disabled={accountEnabled && ACCOUNT_REQUIRED && !email} onPress={() => { if (!p.priorities.length) p.setPriorities(['value']); p.finish(); go(routes.scan); }}>{t('welcome.start')}</Button>}
    </div>
  );
}
