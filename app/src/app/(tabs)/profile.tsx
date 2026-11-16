import { useState } from 'react';
import { Linking, Share, Text, View } from 'react-native';
import Constants from 'expo-constants';
import { api } from '@shared/api/client';
import { t, setLocale } from '@shared/i18n';
import { clearAll } from '@shared/storage';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Image } from 'expo-image';
import { clearCache } from '@/lib/cache';
import { useProfile, useHistory } from '@shared/stores';
import { COUNTRIES, type Country } from '@shared/chains';
import { Body, Cell, Chip, Chips, Confirm, Field, Group, LargeTitle, Muted, Screen, Section, Segmented } from '@/components/ui';
import { useTheme } from '@/lib/theme';

interface Home { city: string; postcode: string | null; lat?: number; lon?: number; label?: string; exact?: boolean }

export default function Profile() {
  const p = useProfile(), hist = useHistory(), c = useTheme();
  const [q, setQ] = useState(''), [sugg, setSugg] = useState<Home[]>([]), [askErase, setAskErase] = useState(false);
  const type = async (v: string) => {
    setQ(v);
    setSugg(v.trim().length < 3 ? [] : await api.searchAddress(v).catch(() => []));
  };
  const exp = async () => {
    const d = { server: await api.exportData().catch(() => null), device: hist.exportAll(), zone: p.zone };
    await Share.share({ message: JSON.stringify(d, null, 1) }).catch(() => undefined);
  };
  const erase = async () => {
    await api.deleteAccount().catch(() => undefined); hist.clear(); clearAll(); p.reset();
    // Everything else the app keeps on the phone: any remaining stored keys, the in-memory answers and the cached photos.
    clearCache(); await AsyncStorage.clear().catch(() => undefined); await Image.clearDiskCache().catch(() => undefined); Image.clearMemoryCache().catch(() => undefined);
  };
  return (
    <Screen title={t('profile.title')} bottom={110}>
      <LargeTitle>{t('profile.title')}</LargeTitle>
      <Section title={t('simple.loc')}>
        <Field value={p.name ?? ''} onChangeText={p.setName} placeholder={t('about.namePh')} autoComplete="given-name" textContentType="givenName" />
        <Field value={q} onChangeText={type} placeholder={p.place ? (p.place.label ?? ([p.place.city, p.place.postcode].filter(Boolean).join(' · ') || t('about.addrPh'))) : t('about.addrPh')} textContentType="fullStreetAddress" />
        {sugg.length > 0 && <Group>{sugg.map((a) => <Cell key={a.label} onPress={() => { p.setPlace(a); setQ(''); setSugg([]); }}><Body>{a.label}</Body></Cell>)}</Group>}
        <Muted small>{t('about.homeHint')}</Muted>
      </Section>
      <Section title={t('profile.language')}>
        <Segmented value={p.language ?? 'fr'} onChange={(k) => { p.setLanguage(k as 'fr' | 'en'); setLocale(k); }} options={[{ key: 'fr', label: 'Français' }, { key: 'en', label: 'English' }]} />
      </Section>
      {COUNTRIES.length > 1 && <Section title={t('profile.country')}>
        <Segmented value={p.country ?? 'FR'} onChange={(k) => p.setCountry(k as Country)} options={COUNTRIES.map((x) => ({ key: x, label: t('country.' + x) }))} />
        {p.country === 'US' && <Muted small>{t('country.usNote')}</Muted>}
      </Section>}
      <Section title={t('profile.diet')}>
        <Segmented value={p.diet} onChange={(k) => p.setDiet(k as 'omnivore' | 'vegetarian' | 'vegan')} options={(['omnivore', 'vegetarian', 'vegan'] as const).map((d) => ({ key: d, label: t('diets.' + d) }))} />
      </Section>
      <Section title={t('profile.restrictions')}>
        <Chips>{['gluten', 'milk', 'peanuts', 'nuts'].map((a) => <Chip key={a} on={p.allergens.includes(a)} onPress={() => p.toggleAllergen(a)}>{t('diets.' + a)}</Chip>)}</Chips>
      </Section>
      <Section title={t('profile.contactTitle')}>
        <Group>
          <Cell chevron onPress={() => Linking.openURL(`mailto:bonjourmieuxmanger@gmail.com?subject=${encodeURIComponent(t('profile.contactSubject'))}`)}>
            <Body>{t('profile.contact')}</Body><Muted small>{t('profile.contactSub')} · bonjourmieuxmanger@gmail.com</Muted>
          </Cell>
        </Group>
      </Section>
      <Section title={t('profile.localTitle')}>
        <Group>
          <Cell chevron onPress={exp}><Body>{t('profile.export')}</Body></Cell>
          <Cell onPress={() => setAskErase(true)}><Text style={{ color: c.bad, fontSize: 16 }}>{t('profile.erase')}</Text></Cell>
        </Group>
      </Section>
      <Confirm open={askErase} onClose={() => setAskErase(false)} onConfirm={erase} title={t('profile.erase')} action={t('profile.erase')}>{t('profile.eraseConfirm')}</Confirm>
      <View><Muted small style={{ textAlign: 'center' }}>{t('brand.credit')}</Muted><Muted small style={{ textAlign: 'center' }}>Mieux {Constants.expoConfig?.version}</Muted></View>
    </Screen>
  );
}
