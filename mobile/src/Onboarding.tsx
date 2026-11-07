import { Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { t, setLocale } from '@shared/i18n';
import { useProfile } from '@shared/stores';
import { COUNTRIES, type Country } from '@shared/chains';
import { Brand, Button, Card, LargeTitle, Muted, Screen, Segmented, useTheme } from './ui';
import { routes } from './nav';
import * as hx from './haptics';

/** Onboarding: the same single screen as the web app (language, brand, three points, country, start). */
export default function Onboarding() {
  const c = useTheme();
  const p = useProfile();
  const router = useRouter();
  const start = () => {
    if (!p.priorities.length) p.setPriorities(['value']);
    hx.success();
    p.finish();
    router.replace(routes.scan);
  };
  return (
    <Screen>
      <Segmented value={p.language ?? 'fr'} onChange={(k) => { p.setLanguage(k as 'fr' | 'en'); setLocale(k); }} options={[{ key: 'fr', label: 'Français' }, { key: 'en', label: 'English' }]} />
      <View style={{ flex: 1, justifyContent: 'center', paddingVertical: 28 }}>
        <Brand size={52} />
        <Muted style={{ marginTop: 6, marginBottom: 18 }}>{t('brand.tagline')}</Muted>
        <LargeTitle>{t('welcome.title')}</LargeTitle>
        <View style={{ marginTop: 12 }}>
          {[t('welcome.p1'), t('welcome.p2'), t('welcome.p3')].map((x) => (
            <View key={x} style={{ flexDirection: 'row', gap: 8, marginVertical: 4 }}>
              <Text style={{ color: c.accent }}>•</Text><Text style={{ color: c.ink, flex: 1 }}>{x}</Text>
            </View>
          ))}
        </View>
      </View>
      {COUNTRIES.length > 1 ? <Card><Segmented value={p.country ?? 'FR'} onChange={(k) => p.setCountry(k as Country)} options={COUNTRIES.map((x) => ({ key: x, label: t('country.' + x) }))} /></Card> : null}
      <Button primary onPress={start}>{t('welcome.start')}</Button>
    </Screen>
  );
}
