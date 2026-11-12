import { t, setLocale } from '@shared/i18n';
import { useProfile } from '@shared/stores';
import { routes, useNav } from '../nav';
import { Button, Brand, Segmented } from '../ui';
import { COUNTRIES, type Country } from '@shared/chains';

export default function Onboarding() {
  const p = useProfile();
  const { go } = useNav();   // when onboarding ends the person lands on the scanner, wherever the URL pointed
  return (
    <div className="ob">
      <Segmented value={p.language ?? 'fr'} onChange={(k) => { p.setLanguage(k as 'fr' | 'en'); setLocale(k as 'fr' | 'en'); }} options={[{ key: 'fr', label: 'Français' }, { key: 'en', label: 'English' }]} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <Brand size={52} big /><p className="mut" style={{ margin: '6px 0 18px' }}>{t('brand.tagline')}</p><h1 style={{ fontSize: 34 }}>{t('welcome.title')}</h1><ul className="ob-points"><li>{t('welcome.p1')}</li><li>{t('welcome.p2')}</li><li>{t('welcome.p3')}</li></ul>
      </div>
      {COUNTRIES.length > 1 && <Segmented value={p.country ?? 'FR'} onChange={(k) => p.setCountry(k as Country)} options={COUNTRIES.map((c) => ({ key: c, label: t('country.' + c) }))} />}
      <Button primary onPress={() => { if (!p.priorities.length) p.setPriorities(['value']); p.finish(); go(routes.scan); }}>{t('welcome.start')}</Button>
    </div>
  );
}
