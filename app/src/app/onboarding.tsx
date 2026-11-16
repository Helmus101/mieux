import { View } from 'react-native';
import { t, setLocale } from '@shared/i18n';
import { useProfile } from '@shared/stores';
import { COUNTRIES, type Country } from '@shared/chains';
import { Body, Brand, Button, Muted, Screen, Segmented } from '@/components/ui';

export default function Onboarding() {
  const p = useProfile();
  return (
    <Screen scroll={false}>
      <Segmented value={p.language ?? 'fr'} onChange={(k) => { p.setLanguage(k as 'fr' | 'en'); setLocale(k); }} options={[{ key: 'fr', label: 'Français' }, { key: 'en', label: 'English' }]} />
      <View style={{ flex: 1, justifyContent: 'center', gap: 14 }}>
        <Brand size={52} />
        <Muted>{t('brand.tagline')}</Muted>
        <Body style={{ fontSize: 32, fontWeight: '700' }}>{t('welcome.title')}</Body>
        {['p1', 'p2', 'p3'].map((k) => <Body key={k}>• {t('welcome.' + k)}</Body>)}
      </View>
      {COUNTRIES.length > 1 && <Segmented value={p.country ?? 'FR'} onChange={(k) => p.setCountry(k as Country)} options={COUNTRIES.map((c) => ({ key: c, label: t('country.' + c) }))} />}
      <Button primary onPress={() => { if (!p.priorities.length) p.setPriorities(['value']); p.finish(); }}>{t('welcome.start')}</Button>
    </Screen>
  );
}
